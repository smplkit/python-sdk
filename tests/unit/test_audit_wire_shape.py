"""Wire-body shape tests for the audit wrapper.

These tests intercept the actual HTTP request the SDK posts and assert
on the JSON envelope key-by-key. They guard against regressions where
the wrapper invents keys outside the documented schema (the snapshot
collapse incident in 3.2.21 shipped because no test asserted on the
bytes; the generated client compiled cleanly without the field, the
wrapper kept emitting it, and CI was none the wiser).

The whitelist of allowed POST/PUT attributes is taken from the audit
service's OpenAPI spec, not the generated client (which is itself a
projection of the spec). Read-only fields (created_at, actor_*,
idempotency_key, version, etc.) MUST NOT appear in request bodies.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from smplkit.audit import (
    AuditClient,
    ForwarderHttp,
    HttpHeader,
)


JSONAPI = "application/vnd.api+json"

FWD_ID = UUID("11111111-2222-3333-4444-555555555555")


# Whitelist from openapi/audit.json -- POST /api/v1/events allows only
# these attributes. created_at, actor_*, idempotency_key are readOnly.
_EVENT_POST_ATTRS = {
    "action",
    "resource_type",
    "resource_id",
    "occurred_at",
    "data",
    "do_not_forward",
}

# POST /api/v1/forwarders allows only these attributes. slug is
# x-immutable (server-derived). created_at/updated_at/deleted_at/version
# are readOnly.
_FORWARDER_POST_ATTRS = {
    "name",
    "forwarder_type",
    "http",
    "enabled",
    "filter",
    "transform",
    "data",
}


def _client_capturing_body(
    captured: list[dict[str, Any]], status: int = 201, response_body: dict | None = None
) -> AuditClient:
    """Build an AuditClient whose mock transport stores each request body."""

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(
            {
                "method": req.method,
                "path": req.url.path,
                "headers": dict(req.headers),
                "json": json.loads(req.content.decode()) if req.content else None,
            }
        )
        return httpx.Response(status, json=response_body or {})

    transport = httpx.MockTransport(handler)
    c = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    c._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    return c


def _event_response_body(event_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, Any]:
    return {
        "data": {
            "id": event_id,
            "type": "event",
            "attributes": {
                "action": "invoice.created",
                "resource_type": "invoice",
                "resource_id": "inv-1",
                "occurred_at": "2026-05-06T12:00:00+00:00",
                "created_at": "2026-05-06T12:00:01+00:00",
                "actor_type": "API_KEY",
                "actor_id": None,
                "actor_label": "",
                "data": {},
                "idempotency_key": "k-1",
            },
        }
    }


def _forwarder_response_body(name: str = "Datadog production") -> dict[str, Any]:
    return {
        "data": {
            "id": str(FWD_ID),
            "type": "forwarder",
            "attributes": {
                "name": name,
                "slug": name.lower().replace(" ", "_"),
                "forwarder_type": "datadog",
                "enabled": True,
                "filter": None,
                "transform": None,
                "http": {
                    "method": "POST",
                    "url": "https://siem.example.com/in",
                    "headers": [{"name": "DD-API-KEY", "value": "<redacted>"}],
                    "body": None,
                    "success_status": "2xx",
                },
                "data": {},
                "created_at": "2026-05-07T12:00:00+00:00",
                "updated_at": "2026-05-07T12:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        }
    }


# ---------------------------------------------------------------------------
# events.record — wire body for every input parameter
# ---------------------------------------------------------------------------


class TestEventsRecordWireShape:
    def test_all_parameters_present_serialize_to_documented_shape(self):
        """Happy-path: every parameter the wrapper accepts shows up on the wire
        in the location the audit service expects (data.attributes.<field>),
        with no extras and no read-only fields."""
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_event_response_body())
        try:
            c.events.record(
                action="invoice.created",
                resource_type="invoice",
                resource_id="inv-1",
                occurred_at=datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
                data={"snapshot": {"total_cents": 4900}, "request_id": "req-1"},
                idempotency_key="k-1",
                do_not_forward=True,
            )
            c.events.flush(timeout=2.0)
        finally:
            c._close()

        assert captured, "buffer should have flushed exactly one POST"
        body = captured[0]["json"]

        # JSON:API envelope shape.
        assert set(body.keys()) == {"data"}
        assert body["data"]["type"] == "event"
        # ID is a placeholder on POST -- server assigns. The Python wrapper
        # sends "" because the generated EventResource model marks id required.
        assert body["data"]["id"] == ""

        attrs = body["data"]["attributes"]
        assert attrs["action"] == "invoice.created"
        assert attrs["resource_type"] == "invoice"
        assert attrs["resource_id"] == "inv-1"
        assert attrs["occurred_at"].startswith("2026-05-06T12:00:00")
        assert attrs["data"] == {
            "snapshot": {"total_cents": 4900},
            "request_id": "req-1",
        }
        assert attrs["do_not_forward"] is True

        # Idempotency-Key is a HEADER, not a body attribute.
        assert "idempotency_key" not in attrs
        assert captured[0]["headers"].get("idempotency-key") == "k-1"

    def test_minimal_call_omits_optional_attributes(self):
        """A bare record(action, resource_type, resource_id) must not invent
        optional fields. occurred_at/data/do_not_forward should be absent."""
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_event_response_body())
        try:
            c.events.record(
                action="invoice.created",
                resource_type="invoice",
                resource_id="inv-1",
            )
            c.events.flush(timeout=2.0)
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        assert attrs.keys() == {"action", "resource_type", "resource_id"}

    def test_do_not_forward_false_is_omitted_to_match_server_default(self):
        """The server default for do_not_forward is False. The wrapper must
        omit the field when the caller passes False (or doesn't pass it),
        rather than emit do_not_forward=False explicitly -- otherwise we
        burn body bytes restating the default."""
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_event_response_body())
        try:
            c.events.record(
                action="x",
                resource_type="y",
                resource_id="z",
                do_not_forward=False,
            )
            c.events.flush(timeout=2.0)
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        assert "do_not_forward" not in attrs

    def test_no_top_level_snapshot_field_appears_on_the_wire(self):
        """Regression guard for the 3.2.21 incident. Even when the caller
        nests a snapshot inside `data`, the wrapper must NOT lift it to a
        top-level `snapshot` attribute (the server schema has no such
        field; FastAPI now strict-rejects it)."""
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_event_response_body())
        try:
            c.events.record(
                action="invoice.created",
                resource_type="invoice",
                resource_id="inv-1",
                data={"snapshot": {"total_cents": 4900}},
            )
            c.events.flush(timeout=2.0)
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        assert "snapshot" not in attrs
        # And it IS still nested in data -- caller's snapshot survives.
        assert attrs["data"]["snapshot"] == {"total_cents": 4900}

    def test_attributes_set_is_subset_of_documented_post_schema(self):
        """No-extra-keys gate: every key emitted on the wire must come from
        the EventResource POST whitelist. This is the catch-all that would
        have flagged the snapshot bug, and will flag the next one."""
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_event_response_body())
        try:
            c.events.record(
                action="invoice.created",
                resource_type="invoice",
                resource_id="inv-1",
                occurred_at=datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
                data={"k": "v"},
                idempotency_key="k-1",
                do_not_forward=True,
            )
            c.events.flush(timeout=2.0)
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        unexpected = set(attrs.keys()) - _EVENT_POST_ATTRS
        assert unexpected == set(), f"wire body has undocumented fields: {unexpected}"


# ---------------------------------------------------------------------------
# forwarders.create — wire body for every input parameter
# ---------------------------------------------------------------------------


class TestForwardersCreateWireShape:
    def test_all_parameters_present_serialize_to_documented_shape(self):
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_forwarder_response_body())
        try:
            c.forwarders.create(
                name="Datadog production",
                forwarder_type="datadog",
                http=ForwarderHttp(
                    method="POST",
                    url="https://siem.example.com/in",
                    headers=[HttpHeader(name="DD-API-KEY", value="real-secret")],
                    body=None,
                    success_status="2xx",
                ),
                enabled=False,
                filter={"==": [{"var": "action"}, "user.created"]},
                transform="$",
                data={"team": "platform"},
            )
        finally:
            c._close()

        assert captured, "expected exactly one POST"
        assert captured[0]["method"] == "POST"
        body = captured[0]["json"]
        assert set(body.keys()) == {"data"}
        assert body["data"]["type"] == "forwarder"
        # POST: server assigns id, wrapper sends "".
        assert body["data"]["id"] == ""

        attrs = body["data"]["attributes"]
        assert attrs["name"] == "Datadog production"
        assert attrs["forwarder_type"] == "datadog"
        assert attrs["enabled"] is False
        assert attrs["filter"] == {"==": [{"var": "action"}, "user.created"]}
        assert attrs["transform"] == "$"
        assert attrs["data"] == {"team": "platform"}
        assert attrs["http"] == {
            "method": "POST",
            "url": "https://siem.example.com/in",
            "headers": [{"name": "DD-API-KEY", "value": "real-secret"}],
            "body": None,
            "success_status": "2xx",
        }

        # Read-only / immutable fields MUST NOT appear on the wire.
        for read_only in ("slug", "created_at", "updated_at", "deleted_at", "version"):
            assert read_only not in attrs

    def test_minimal_call_omits_optional_attributes(self):
        """name + forwarder_type + http are required; everything else
        is optional. enabled defaults to True at the wrapper layer; the
        rest must not be invented."""
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_forwarder_response_body())
        try:
            c.forwarders.create(
                name="x",
                forwarder_type="http",
                http=ForwarderHttp(url="https://x"),
            )
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        # Required + the default-True enabled, plus the http object.
        assert "name" in attrs
        assert "forwarder_type" in attrs
        assert "http" in attrs
        assert attrs["enabled"] is True
        for opt in ("filter", "transform", "data"):
            assert opt not in attrs

    def test_attributes_set_is_subset_of_documented_post_schema(self):
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, response_body=_forwarder_response_body())
        try:
            c.forwarders.create(
                name="Datadog production",
                forwarder_type="datadog",
                http=ForwarderHttp(url="https://x"),
                enabled=True,
                filter={"==": [1, 1]},
                transform="$",
                data={"k": "v"},
            )
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        unexpected = set(attrs.keys()) - _FORWARDER_POST_ATTRS
        assert unexpected == set(), f"wire body has undocumented fields: {unexpected}"


# ---------------------------------------------------------------------------
# forwarders.update — wire body for every input parameter
# ---------------------------------------------------------------------------


class TestForwardersUpdateWireShape:
    def test_all_parameters_present_serialize_to_documented_shape(self):
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(
            captured,
            status=200,
            response_body=_forwarder_response_body(name="Renamed"),
        )
        try:
            c.forwarders.update(
                FWD_ID,
                name="Renamed",
                forwarder_type="datadog",
                http=ForwarderHttp(
                    url="https://siem.example.com/in",
                    headers=[HttpHeader(name="X-K", value="real-secret")],
                ),
                enabled=False,
                filter={"==": [1, 1]},
                transform="$",
                data={"k": "v"},
            )
        finally:
            c._close()

        assert captured[0]["method"] == "PUT"
        body = captured[0]["json"]
        assert body["data"]["type"] == "forwarder"
        # On PUT the wrapper echoes the path id into the envelope id.
        assert body["data"]["id"] == str(FWD_ID)

        attrs = body["data"]["attributes"]
        assert attrs["name"] == "Renamed"
        assert attrs["forwarder_type"] == "datadog"
        assert attrs["enabled"] is False
        assert attrs["filter"] == {"==": [1, 1]}
        assert attrs["transform"] == "$"
        assert attrs["data"] == {"k": "v"}
        # Headers carry the real plaintext value the caller supplied --
        # the wrapper does NOT round-trip the redacted GET response.
        assert attrs["http"]["headers"] == [{"name": "X-K", "value": "real-secret"}]

        for read_only in ("slug", "created_at", "updated_at", "deleted_at", "version"):
            assert read_only not in attrs

    def test_attributes_set_is_subset_of_documented_post_schema(self):
        captured: list[dict[str, Any]] = []
        c = _client_capturing_body(captured, status=200, response_body=_forwarder_response_body())
        try:
            c.forwarders.update(
                FWD_ID,
                name="x",
                forwarder_type="http",
                http=ForwarderHttp(url="https://x"),
                enabled=True,
                filter={"x": 1},
                transform="$",
                data={"k": "v"},
            )
        finally:
            c._close()

        attrs = captured[0]["json"]["data"]["attributes"]
        unexpected = set(attrs.keys()) - _FORWARDER_POST_ATTRS
        assert unexpected == set(), f"wire body has undocumented fields: {unexpected}"
