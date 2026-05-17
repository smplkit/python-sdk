"""Tests for the audit forwarders management surface.

The httpx.MockTransport pattern is reused here — none of these tests
touch the network. Coverage target is 100% on every line in
``smplkit.management.audit``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import pytest

from smplkit import Error, NotFoundError, PaymentRequiredError
from smplkit._generated.audit.client import AuthenticatedClient as _AuditAuthClient
from smplkit.audit import (
    Forwarder,
    HttpConfiguration,
    HttpHeader,
)
from smplkit.management.audit import AuditClient


JSONAPI = "application/vnd.api+json"

FWD_ID = UUID("11111111-2222-3333-4444-555555555555")


def _forwarder_resource(
    *,
    id_: UUID = FWD_ID,
    name: str = "Datadog production",
    description: str | None = None,
    enabled: bool = True,
    forwarder_type: str = "DATADOG",
    filter_: dict[str, Any] | None = None,
    transform: str | None = None,
    transform_type: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(id_),
        "type": "forwarder",
        "attributes": {
            "name": name,
            "forwarder_type": forwarder_type,
            "enabled": enabled,
            "description": description,
            "filter": filter_,
            "transform": transform,
            "transform_type": transform_type,
            "configuration": {
                "method": "POST",
                "url": "https://siem.example.com/in",
                "headers": [{"name": "DD-API-KEY", "value": "<redacted>"}],
                "success_status": "2xx",
            },
            "created_at": "2026-05-07T12:00:00+00:00",
            "updated_at": "2026-05-07T12:00:00+00:00",
            "deleted_at": None,
            "version": 1,
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

    def test_http_configuration_round_trip(self):
        h = HttpConfiguration(
            method="PUT",
            url="https://x.example/in",
            headers=[HttpHeader(name="A", value="1")],
            success_status="200",
        )
        d = h._to_dict()
        again = HttpConfiguration._from_dict(d)
        assert again == h

    def test_http_configuration_from_dict_defaults(self):
        # Empty dict should produce a sane default HttpConfiguration.
        h = HttpConfiguration._from_dict({})
        assert h.method == "POST"
        assert h.headers == []
        assert h.success_status == "2xx"

    def test_forwarder_from_resource(self):
        f = Forwarder._from_resource(_forwarder_resource())
        assert f.id == FWD_ID
        assert f.name == "Datadog production"
        assert f.configuration.headers[0].value == "<redacted>"
        assert f.version == 1
        assert f.deleted_at is None
        assert f.description is None
        assert f.transform_type is None


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
        fwd = c.forwarders.create(
            name="Datadog production",
            forwarder_type="DATADOG",
            configuration=HttpConfiguration(
                url="https://siem.example.com/in",
                headers=[HttpHeader(name="DD-API-KEY", value="real-secret")],
            ),
            description="Forwards user.* events.",
            filter={"==": [{"var": "action"}, "user.created"]},
            transform="$",
        )
        assert fwd.name == "Datadog production"
        assert captured["method"] == "POST"
        assert "/api/v1/forwarders" in captured["url"]
        # The transform survives the round-trip; the on-the-wire body must
        # carry it before the server redacts headers on the read. The
        # description and transform_type also need to reach the server.
        assert "user.created" in captured["body"]
        assert "Forwards user.* events." in captured["body"]
        assert "JSONATA" in captured["body"]

    def test_create_accepts_dict_configuration(self):
        def handler(req):
            return httpx.Response(201, json={"data": _forwarder_resource()})

        c = _client_with_handler(handler)
        fwd = c.forwarders.create(
            name="x",
            forwarder_type="HTTP",
            configuration={
                "method": "POST",
                "url": "https://x",
                "headers": [{"name": "h", "value": "v"}],
                "success_status": "2xx",
            },
        )
        assert fwd.id == FWD_ID

    def test_create_402_raises_payment_required(self):
        # The audit service no longer returns 402 on forwarder creation
        # (configuration is plan-agnostic — see ADR-047), but the
        # wrapper's status-to-exception mapping should still surface
        # 402 as PaymentRequiredError if any future endpoint does.
        def handler(req):
            return httpx.Response(402, json={"errors": [{"status": "402"}]})

        c = _client_with_handler(handler)
        with pytest.raises(PaymentRequiredError):
            c.forwarders.create(
                name="x",
                forwarder_type="HTTP",
                configuration=HttpConfiguration(url="https://x"),
            )

    def test_list_paginates(self):
        pages = [
            {
                "data": [_forwarder_resource(name="A")],
                "meta": {"pagination": {"page": 1, "size": 1, "total": 2, "total_pages": 2}},
            },
            {
                "data": [_forwarder_resource(name="B")],
                "meta": {"pagination": {"page": 2, "size": 1, "total": 2, "total_pages": 2}},
            },
        ]
        call_count = [0]

        def handler(req):
            page = pages[call_count[0]]
            call_count[0] += 1
            return httpx.Response(200, json=page)

        c = _client_with_handler(handler)
        first = c.forwarders.list(
            page_size=1,
            page_number=1,
            meta_total=True,
            forwarder_type="DATADOG",
            enabled=True,
        )
        assert len(first.forwarders) == 1
        assert first.pagination["total"] == 2
        assert first.pagination["page"] == 1
        iterated = list(first)
        assert len(iterated) == 1

        second = c.forwarders.list(page_size=1, page_number=2, meta_total=True)
        assert second.pagination["page"] == 2

    def test_get(self):
        def handler(req):
            assert str(FWD_ID) in req.url.path
            return httpx.Response(200, json={"data": _forwarder_resource()})

        c = _client_with_handler(handler)
        fwd = c.forwarders.get(FWD_ID)
        assert fwd.id == FWD_ID
        # str id also accepted.
        fwd2 = c.forwarders.get(str(FWD_ID))
        assert fwd2.id == FWD_ID

    def test_update(self):
        def handler(req):
            assert req.method == "PUT"
            return httpx.Response(200, json={"data": _forwarder_resource(name="Renamed")})

        c = _client_with_handler(handler)
        fwd = c.forwarders.update(
            FWD_ID,
            name="Renamed",
            forwarder_type="DATADOG",
            configuration=HttpConfiguration(url="https://x"),
            enabled=False,
            filter={"==": [1, 1]},
            transform="$",
        )
        assert fwd.name == "Renamed"

    def test_delete(self):
        captured: dict[str, str] = {}

        def handler(req):
            captured["method"] = req.method
            return httpx.Response(204)

        c = _client_with_handler(handler)
        c.forwarders.delete(FWD_ID)
        # str id also accepted.
        c.forwarders.delete(str(FWD_ID))
        assert captured["method"] == "DELETE"

    def test_delete_404_raises_not_found(self):
        def handler(req):
            return httpx.Response(404, json={"errors": []})

        c = _client_with_handler(handler)
        with pytest.raises(NotFoundError):
            c.forwarders.delete(FWD_ID)

    def test_delete_unexpected_2xx_raises_error(self):
        # Defensive: delete expects 204; a 200 response (server bug)
        # surfaces as a generic Error rather than passing silently.
        def handler(req):
            return httpx.Response(200, json={})

        c = _client_with_handler(handler)
        with pytest.raises(Error):
            c.forwarders.delete(FWD_ID)

    def test_create_unexpected_2xx_status_raises_error(self):
        def handler(req):
            return httpx.Response(200, json={})

        c = _client_with_handler(handler)
        with pytest.raises(Error):
            c.forwarders.create(
                name="x",
                forwarder_type="HTTP",
                configuration=HttpConfiguration(url="https://x"),
            )


def test_async_client_exposes_forwarders():
    """The management ``AsyncAuditClient`` mirrors the sync one — the
    forwarders surface must reach async callers."""
    from smplkit.management.audit import AsyncAuditClient

    auth = _AuditAuthClient(base_url="https://audit.example.com", token="sk_api_test")
    c = AsyncAuditClient(auth_client=auth)
    assert c.forwarders is not None
