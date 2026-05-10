"""Tests for the audit events management surface — ``mgmt.audit.events.*``.

The runtime-side ``client.audit.events.record`` (fire-and-forget) is
covered in ``tests/unit/test_audit.py`` and
``tests/unit/test_audit_coverage.py``. This file covers the
management-side ``list`` and ``get`` reads.
"""
from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from smplkit._generated.audit.client import AuthenticatedClient as _AuditAuthClient
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit.audit import Event
from smplkit.management.audit import AuditClient, EventListPage


def _client_with_handler(handler) -> AuditClient:
    auth = _AuditAuthClient(
        base_url="https://audit.example.com", token="sk_api_test"
    )
    auth.set_httpx_client(
        httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://audit.example.com",
        )
    )
    return AuditClient(auth_client=auth)


def _event_resource(event_id: str = "11111111-2222-3333-4444-555555555555") -> dict:
    return {
        "id": event_id,
        "type": "event",
        "attributes": {
            "action": "user.created",
            "resource_type": "user",
            "resource_id": "u-1",
            "occurred_at": "2026-05-06T12:00:00+00:00",
            "created_at": "2026-05-06T12:00:01+00:00",
            "actor_type": "API_KEY",
            "actor_id": None,
            "actor_label": "",
            "data": {},
            "idempotency_key": "k",
        },
    }


class TestList:
    def test_threads_filter_and_pagination_params(self):
        seen_urls: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            seen_urls.append(str(req.url))
            return httpx.Response(
                200,
                json={"data": [], "links": {}, "meta": {"page_size": 50}},
            )

        client = _client_with_handler(handler)
        client.events.list(
            action="user.created",
            resource_type="user",
            resource_id="u-1",
            actor_type="USER",
            actor_id=UUID("11111111-2222-3333-4444-555555555555"),
            occurred_at_range="[2026-04-01T00:00:00Z,*)",
            page_size=25,
            page_after="abc",
        )
        u = seen_urls[0]
        for needle in [
            "filter%5Baction%5D=user.created",
            "filter%5Bresource_type%5D=user",
            "filter%5Bresource_id%5D=u-1",
            "filter%5Bactor_type%5D=USER",
            "filter%5Boccurred_at%5D=",
            "page%5Bsize%5D=25",
            "page%5Bafter%5D=abc",
        ]:
            assert needle in u

    def test_paginates(self):
        pages = [
            {
                "data": [_event_resource("11111111-1111-1111-1111-111111111111")],
                "links": {"next": "/api/v1/events?page[size]=1&page[after]=tok-2"},
                "meta": {"page_size": 1},
            },
            {
                "data": [_event_resource("22222222-2222-2222-2222-222222222222")],
                "meta": {"page_size": 1},
            },
        ]
        call_count = [0]

        def handler(req):
            page = pages[call_count[0]]
            call_count[0] += 1
            return httpx.Response(200, json=page)

        client = _client_with_handler(handler)
        first = client.events.list(page_size=1)
        assert len(first.events) == 1
        assert first.next_cursor == "tok-2"
        second = client.events.list(page_size=1, page_after=first.next_cursor)
        assert len(second.events) == 1
        assert second.next_cursor is None

    def test_unexpected_status_on_5xx(self):
        client = _client_with_handler(lambda req: httpx.Response(503, json={}))
        with pytest.raises(UnexpectedStatus):
            client.events.list()

    def test_event_list_page_iter_and_len(self):
        client = _client_with_handler(
            lambda req: httpx.Response(
                200,
                json={"data": [_event_resource()], "meta": {"page_size": 1}},
            )
        )
        page = client.events.list()
        assert isinstance(page, EventListPage)
        assert len(page) == 1
        assert [e.id for e in page] == [
            UUID("11111111-2222-3333-4444-555555555555")
        ]


class TestGet:
    def test_round_trips(self):
        event_id = UUID("11111111-2222-3333-4444-555555555555")

        def handler(req: httpx.Request) -> httpx.Response:
            assert str(event_id) in req.url.path
            return httpx.Response(200, json={"data": _event_resource(str(event_id))})

        client = _client_with_handler(handler)
        ev = client.events.get(event_id)
        assert ev.id == event_id
        assert ev.action == "user.created"

    def test_get_string_id_accepts_str(self):
        event_id = "11111111-2222-3333-4444-555555555555"
        client = _client_with_handler(
            lambda req: httpx.Response(
                200, json={"data": _event_resource(event_id)}
            )
        )
        ev = client.events.get(event_id)
        assert ev.id == UUID(event_id)

    def test_raises_for_404(self):
        client = _client_with_handler(lambda req: httpx.Response(404, json={}))
        with pytest.raises(UnexpectedStatus):
            client.events.get(UUID("00000000-0000-0000-0000-000000000099"))

    def test_event_model_round_trips_z_suffix_timestamps(self):
        # Defensive: the Event model accepts trailing-Z timestamps that
        # JS clients commonly produce.
        ev = Event._from_resource(
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "type": "event",
                "attributes": {
                    "action": "x",
                    "resource_type": "y",
                    "resource_id": "z",
                    "occurred_at": "2026-05-06T12:00:00Z",
                    "created_at": "2026-05-06T12:00:01Z",
                    "actor_type": "API_KEY",
                    "actor_label": "",
                },
            }
        )
        assert ev.occurred_at.tzinfo is not None
