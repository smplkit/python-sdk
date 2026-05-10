"""Tests for the audit forwarders / functions management surface.

The httpx.MockTransport pattern is reused here — none of these tests
touch the network. Coverage target is 100% on every line in
``smplkit.management.audit`` for the forwarder + functions paths.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import pytest

from smplkit._generated.audit.client import AuthenticatedClient as _AuditAuthClient
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit.audit import (
    Forwarder,
    ForwarderDelivery,
    ForwarderHttp,
    HttpHeader,
    RetryFailedDeliveriesSummary,
    TestForwarderResult,
)
from smplkit.management.audit import AuditClient


JSONAPI = "application/vnd.api+json"

FWD_ID = UUID("11111111-2222-3333-4444-555555555555")
DELIVERY_ID = UUID("22222222-3333-4444-5555-666666666666")
EVENT_ID = UUID("33333333-4444-5555-6666-777777777777")


def _forwarder_resource(
    *,
    id_: UUID = FWD_ID,
    name: str = "Datadog production",
    enabled: bool = True,
    forwarder_type: str = "datadog",
    filter_: dict[str, Any] | None = None,
    transform: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(id_),
        "type": "forwarder",
        "attributes": {
            "name": name,
            "slug": name.lower().replace(" ", "_"),
            "forwarder_type": forwarder_type,
            "enabled": enabled,
            "filter": filter_,
            "transform": transform,
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


def _delivery_resource(*, status: str = "succeeded") -> dict[str, Any]:
    return {
        "id": str(DELIVERY_ID),
        "type": "forwarder_delivery",
        "attributes": {
            "forwarder_id": str(FWD_ID),
            "event_id": str(EVENT_ID),
            "attempt_number": 1,
            "status": status,
            "request": {
                "method": "POST",
                "url": "https://siem.example.com/in",
                "headers": [{"name": "X-K", "value": "<redacted>"}],
                "body": '{"action":"user.created"}',
            },
            "response_status": 202,
            "response_body": "ok",
            "latency_ms": 42,
            "error": None,
            "created_at": "2026-05-07T12:00:01+00:00",
        },
    }


def _client_with_handler(handler) -> AuditClient:
    auth = _AuditAuthClient(base_url="https://audit.example.com", token="sk_api_test")
    auth.set_httpx_client(
        httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://audit.example.com",
        )
    )
    return AuditClient(auth_client=auth)


# ---------------------------------------------------------------------------
# Models — round-trip and edge cases
# ---------------------------------------------------------------------------


class TestModels:
    def test_http_header_to_dict(self):
        h = HttpHeader(name="X-K", value="v")
        assert h._to_dict() == {"name": "X-K", "value": "v"}

    def test_forwarder_http_round_trip(self):
        h = ForwarderHttp(
            method="PUT",
            url="https://x.example/in",
            headers=[HttpHeader(name="A", value="1")],
            body='{"a":1}',
            success_status="200",
        )
        d = h._to_dict()
        again = ForwarderHttp._from_dict(d)
        assert again == h

    def test_forwarder_http_from_dict_defaults(self):
        # Empty dict should produce a sane default ForwarderHttp.
        h = ForwarderHttp._from_dict({})
        assert h.method == "POST"
        assert h.headers == []
        assert h.success_status == "2xx"

    def test_forwarder_from_resource(self):
        f = Forwarder._from_resource(_forwarder_resource())
        assert f.id == FWD_ID
        assert f.slug == "datadog_production"
        assert f.http.headers[0].value == "<redacted>"
        assert f.version == 1
        assert f.deleted_at is None

    def test_forwarder_delivery_from_resource(self):
        d = ForwarderDelivery._from_resource(_delivery_resource(status="failed"))
        assert d.status == "failed"
        assert d.response_status == 202
        assert d.attempt_number == 1


# ---------------------------------------------------------------------------
# Forwarders CRUD
# ---------------------------------------------------------------------------


class TestForwardersCrud:
    def test_create(self):
        captured: dict[str, Any] = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["method"] = req.method
            captured["url"] = str(req.url)
            captured["body"] = req.content.decode()
            return httpx.Response(201, json={"data": _forwarder_resource()}, headers={"content-type": JSONAPI})

        c = _client_with_handler(handler)
        try:
            fwd = c.forwarders.create(
                name="Datadog production",
                forwarder_type="datadog",
                http=ForwarderHttp(
                    url="https://siem.example.com/in",
                    headers=[HttpHeader(name="DD-API-KEY", value="real-secret")],
                ),
                filter={"==": [{"var": "action"}, "user.created"]},
                transform="$",
                data={"team": "platform"},
            )
        finally:
            pass
        assert fwd.slug == "datadog_production"
        assert captured["method"] == "POST"
        assert "/api/v1/forwarders" in captured["url"]
        # The transform survives the round-trip; the on-the-wire body must
        # carry it before the server redacts headers on the read.
        assert "user.created" in captured["body"]

    def test_create_accepts_dict_http(self):
        def handler(req):
            return httpx.Response(201, json={"data": _forwarder_resource()})

        c = _client_with_handler(handler)
        try:
            fwd = c.forwarders.create(
                name="x",
                forwarder_type="http",
                http={
                    "method": "POST",
                    "url": "https://x",
                    "headers": [{"name": "h", "value": "v"}],
                    "body": None,
                    "success_status": "2xx",
                },
            )
        finally:
            pass
        assert fwd.id == FWD_ID

    def test_create_unexpected_status_raises(self):
        def handler(req):
            return httpx.Response(402, json={"errors": [{"status": "402"}]})

        c = _client_with_handler(handler)
        try:
            with pytest.raises(UnexpectedStatus):
                c.forwarders.create(
                    name="x",
                    forwarder_type="http",
                    http=ForwarderHttp(url="https://x"),
                )
        finally:
            pass

    def test_list_paginates(self):
        pages = [
            {
                "data": [_forwarder_resource(name="A")],
                "links": {"next": "/api/v1/forwarders?page[size]=1&page[after]=tok-2"},
                "meta": {"page_size": 1},
            },
            {
                "data": [_forwarder_resource(name="B")],
                "meta": {"page_size": 1},
            },
        ]
        call_count = [0]

        def handler(req):
            page = pages[call_count[0]]
            call_count[0] += 1
            return httpx.Response(200, json=page)

        c = _client_with_handler(handler)
        try:
            first = c.forwarders.list(page_size=1, forwarder_type="datadog", enabled=True)
            assert len(first.forwarders) == 1
            assert first.next_cursor == "tok-2"
            iterated = list(first)
            assert len(iterated) == 1

            second = c.forwarders.list(page_size=1, page_after=first.next_cursor)
            assert second.next_cursor is None
        finally:
            pass

    def test_get(self):
        def handler(req):
            assert str(FWD_ID) in req.url.path
            return httpx.Response(200, json={"data": _forwarder_resource()})

        c = _client_with_handler(handler)
        try:
            fwd = c.forwarders.get(FWD_ID)
            assert fwd.id == FWD_ID
            # str id also accepted.
            fwd2 = c.forwarders.get(str(FWD_ID))
            assert fwd2.id == FWD_ID
        finally:
            pass

    def test_update(self):
        def handler(req):
            assert req.method == "PUT"
            return httpx.Response(200, json={"data": _forwarder_resource(name="Renamed")})

        c = _client_with_handler(handler)
        try:
            fwd = c.forwarders.update(
                FWD_ID,
                name="Renamed",
                forwarder_type="datadog",
                http=ForwarderHttp(url="https://x"),
                enabled=False,
                filter={"==": [1, 1]},
                transform="$",
                data={"k": "v"},
            )
        finally:
            pass
        assert fwd.name == "Renamed"

    def test_delete(self):
        captured: dict[str, str] = {}

        def handler(req):
            captured["method"] = req.method
            return httpx.Response(204)

        c = _client_with_handler(handler)
        try:
            c.forwarders.delete(FWD_ID)
            # str id also accepted.
            c.forwarders.delete(str(FWD_ID))
        finally:
            pass
        assert captured["method"] == "DELETE"

    def test_delete_unexpected_status_raises(self):
        def handler(req):
            return httpx.Response(404, json={"errors": []})

        c = _client_with_handler(handler)
        try:
            with pytest.raises(UnexpectedStatus):
                c.forwarders.delete(FWD_ID)
        finally:
            pass


# ---------------------------------------------------------------------------
# Deliveries
# ---------------------------------------------------------------------------


class TestDeliveries:
    def test_list_with_filters(self):
        pages = [
            {
                "data": [_delivery_resource(status="succeeded")],
                "links": {"next": (f"/api/v1/forwarders/{FWD_ID}/deliveries?page[size]=1&page[after]=tok-2")},
                "meta": {"page_size": 1},
            },
            {
                "data": [_delivery_resource(status="failed")],
                "meta": {"page_size": 1},
            },
        ]
        call_count = [0]

        def handler(req):
            page = pages[call_count[0]]
            call_count[0] += 1
            return httpx.Response(200, json=page)

        c = _client_with_handler(handler)
        try:
            first = c.forwarders.deliveries.list(
                FWD_ID,
                status="succeeded",
                created_at_range="[2020-01-01T00:00:00Z,*)",
                page_size=1,
            )
            assert len(first.deliveries) == 1
            assert list(first)[0].status == "succeeded"
            assert first.next_cursor == "tok-2"

            second = c.forwarders.deliveries.list(FWD_ID, page_after=first.next_cursor)
            assert second.next_cursor is None
        finally:
            pass

    def test_retry_returns_new_row(self):
        def handler(req):
            assert req.method == "POST"
            assert "actions/retry" in req.url.path
            return httpx.Response(200, json={"data": _delivery_resource(status="succeeded")})

        c = _client_with_handler(handler)
        try:
            row = c.forwarders.deliveries.actions.retry(FWD_ID, DELIVERY_ID)
            assert row.status == "succeeded"
            # str ids also accepted.
            row2 = c.forwarders.deliveries.actions.retry(str(FWD_ID), str(DELIVERY_ID))
            assert row2.status == "succeeded"
        finally:
            pass

    def test_bulk_retry_summary(self):
        def handler(req):
            return httpx.Response(200, json={"attempted": 3, "succeeded": 2, "failed": 1})

        c = _client_with_handler(handler)
        try:
            summary = c.forwarders.actions.retry_failed_deliveries(FWD_ID)
        finally:
            pass
        assert summary == RetryFailedDeliveriesSummary(attempted=3, succeeded=2, failed=1)


# ---------------------------------------------------------------------------
# functions.test_forwarder.actions.execute
# ---------------------------------------------------------------------------


class TestExecuteTestForwarder:
    def test_success(self):
        captured: dict[str, Any] = {}

        def handler(req):
            captured["method"] = req.method
            captured["url"] = str(req.url)
            captured["body"] = req.content.decode()
            return httpx.Response(
                200,
                json={
                    "succeeded": True,
                    "response_status": 202,
                    "response_headers": {"X-Echo": "y"},
                    "response_body": "accepted",
                    "latency_ms": 12,
                    "error": None,
                },
            )

        c = _client_with_handler(handler)
        try:
            result = c.functions.test_forwarder.actions.execute(
                url="https://siem.example.com/in",
                headers=[HttpHeader(name="X-K", value="v")],
                body='{"hello":"world"}',
                success_status="2xx",
                timeout_ms=5000,
            )
        finally:
            pass
        assert result == TestForwarderResult(
            succeeded=True,
            response_status=202,
            response_headers={"X-Echo": "y"},
            response_body="accepted",
            latency_ms=12,
            error=None,
        )
        assert "test_forwarder/actions/execute" in captured["url"]

    def test_accepts_dict_headers(self):
        def handler(req):
            return httpx.Response(
                200,
                json={
                    "succeeded": True,
                    "response_status": 200,
                    "response_headers": {},
                    "response_body": "",
                    "latency_ms": 1,
                    "error": None,
                },
            )

        c = _client_with_handler(handler)
        try:
            r = c.functions.test_forwarder.actions.execute(
                url="https://x",
                headers=[{"name": "h", "value": "v"}],
            )
        finally:
            pass
        assert r.succeeded is True

    def test_no_headers_no_timeout(self):
        # Exercises the headers=None branch and the timeout_ms unset branch.
        def handler(req):
            return httpx.Response(
                200,
                json={
                    "succeeded": False,
                    "response_status": 500,
                    "response_headers": {},
                    "response_body": "",
                    "latency_ms": None,
                    "error": "5xx",
                },
            )

        c = _client_with_handler(handler)
        try:
            r = c.functions.test_forwarder.actions.execute(url="https://x")
        finally:
            pass
        assert r.succeeded is False
        assert r.error == "5xx"


# ---------------------------------------------------------------------------
# Event Model
# ---------------------------------------------------------------------------


def test_event_resource_round_trips_do_not_forward():
    """Event._from_resource preserves the do_not_forward flag — the
    forwarder filter logic relies on it surfacing intact through reads."""
    from smplkit.audit.models import Event

    res = {
        "id": str(EVENT_ID),
        "type": "event",
        "attributes": {
            "action": "x",
            "resource_type": "y",
            "resource_id": "z",
            "occurred_at": "2026-05-07T12:00:00+00:00",
            "created_at": "2026-05-07T12:00:01+00:00",
            "actor_type": "API_KEY",
            "actor_label": "",
            "do_not_forward": True,
        },
    }
    ev = Event._from_resource(res)
    assert ev.do_not_forward is True
