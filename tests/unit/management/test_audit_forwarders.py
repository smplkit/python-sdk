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
    ForwarderHttp,
    HttpHeader,
)
from smplkit.management.audit import AuditClient


JSONAPI = "application/vnd.api+json"

FWD_ID = UUID("11111111-2222-3333-4444-555555555555")


def _forwarder_resource(
    *,
    id_: UUID = FWD_ID,
    name: str = "Datadog production",
    enabled: bool = True,
    forwarder_type: str = "DATADOG",
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
            http=ForwarderHttp(
                url="https://siem.example.com/in",
                headers=[HttpHeader(name="DD-API-KEY", value="real-secret")],
            ),
            filter={"==": [{"var": "action"}, "user.created"]},
            transform="$",
        )
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
        fwd = c.forwarders.create(
            name="x",
            forwarder_type="HTTP",
            http={
                "method": "POST",
                "url": "https://x",
                "headers": [{"name": "h", "value": "v"}],
                "body": None,
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
                http=ForwarderHttp(url="https://x"),
            )

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
        first = c.forwarders.list(page_size=1, forwarder_type="DATADOG", enabled=True)
        assert len(first.forwarders) == 1
        assert first.next_cursor == "tok-2"
        iterated = list(first)
        assert len(iterated) == 1

        second = c.forwarders.list(page_size=1, page_after=first.next_cursor)
        assert second.next_cursor is None

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
            http=ForwarderHttp(url="https://x"),
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
                http=ForwarderHttp(url="https://x"),
            )


def test_async_client_exposes_forwarders():
    """The management ``AsyncAuditClient`` mirrors the sync one — the
    forwarders surface must reach async callers."""
    from smplkit.management.audit import AsyncAuditClient

    auth = _AuditAuthClient(base_url="https://audit.example.com", token="sk_api_test")
    c = AsyncAuditClient(auth_client=auth)
    assert c.forwarders is not None
