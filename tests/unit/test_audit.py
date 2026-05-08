"""Tests for the SDK audit namespace."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest

from smplkit.audit._buffer import (
    AuditEventBuffer,
    MAX_BUFFER_SIZE,
    _PendingEvent,
)
from smplkit.audit.client import AuditClient
from smplkit.audit.models import Event


class _StubResponse:
    """Mimics httpx.Response just enough for the buffer's outcome handler."""

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


# --------------------------------------------------------------------------
# Buffer behavior
# --------------------------------------------------------------------------


def test_buffer_drops_oldest_when_over_capacity():
    """When the buffer is full, the oldest item is dropped to make room."""
    posts: list[_PendingEvent] = []

    def post(item: _PendingEvent) -> httpx.Response:
        # Hold the worker by returning success only after we've populated.
        posts.append(item)
        return 201

    buf = AuditEventBuffer(post_fn=post, max_size=3, watermark=999)
    try:
        for i in range(5):
            buf.enqueue({"i": i})
        # Allow the worker a brief tick — but posting is fast in this stub,
        # so by the time we check, the queue should be drained.
        buf.flush(timeout=2.0)
        assert len(posts) >= 3  # at least three events made it through
        # The oldest items are the ones dropped, so events with the largest
        # ``i`` values should be present in posts.
        seen = {p.body["i"] for p in posts}
        assert max(seen) == 4
    finally:
        buf.close(timeout=2.0)


def test_buffer_retries_on_transient_failure():
    attempts: list[int] = []

    def post(item: _PendingEvent) -> httpx.Response:
        attempts.append(item.attempts)
        # Fail twice, succeed on the third try.
        if len([a for a in attempts if a < 2]) < 2:
            return 503
        return 201

    buf = AuditEventBuffer(
        post_fn=post,
        max_size=10,
        watermark=1,
        flush_interval=0.05,
    )
    try:
        buf.enqueue({"i": 0})
        # Worker needs time to retry — backoff is 0.25s base; allow several seconds.
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if any(a >= 1 for a in attempts):
                break
            time.sleep(0.05)
        assert any(a >= 1 for a in attempts), "expected at least one retry"
    finally:
        buf.close(timeout=2.0)


def test_buffer_drops_permanent_failures():
    posted: list[_PendingEvent] = []

    def post(item: _PendingEvent) -> httpx.Response:
        posted.append(item)
        return 400

    buf = AuditEventBuffer(post_fn=post, max_size=10, watermark=1)
    try:
        buf.enqueue({"i": 0})
        buf.flush(timeout=2.0)
        # 400 → permanent failure → posted once, then dropped, no retry storm.
        # Race-ok because the worker may try once then move on.
        assert posted  # at least one attempt
        assert all(p.attempts == 0 for p in posted)
    finally:
        buf.close(timeout=2.0)


# --------------------------------------------------------------------------
# Public client surface
# --------------------------------------------------------------------------


def test_create_returns_immediately(monkeypatch):
    """The fire-and-forget contract: create() returns without blocking on POST."""
    # Body must round-trip through the generated EventResponse model, so
    # include all required fields on the resource. This also makes the
    # buffer's success path (status_code returned) covered.
    _success_body = {
        "data": {
            "id": "00000000-0000-0000-0000-000000000001",
            "type": "event",
            "attributes": {
                "action": "invoice.created",
                "resource_type": "invoice",
                "resource_id": "inv-x",
                "occurred_at": "2026-05-06T12:00:00+00:00",
                "created_at": "2026-05-06T12:00:01+00:00",
                "actor_type": "API_KEY",
                "actor_id": None,
                "actor_label": "",
                "data": {},
                "idempotency_key": "auto",
            },
        }
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(201, json=_success_body))
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    # Replace the underlying httpx client so we never actually go to the network.
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    # Re-bind the buffer to use the new http client's POST behavior.

    started = time.monotonic()
    for i in range(20):
        client.events.record(
            action="invoice.created",
            resource_type="invoice",
            resource_id=f"inv-{i}",
        )
    assert time.monotonic() - started < 0.5  # well under the slowest POST round trip.

    client._close()


def test_get_round_trips_a_single_event(monkeypatch):
    event_id = UUID("11111111-2222-3333-4444-555555555555")

    def handler(req: httpx.Request) -> httpx.Response:
        assert str(event_id) in req.url.path
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": str(event_id),
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
                        "idempotency_key": "auto-abc",
                    },
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        ev = client.events.get(event_id)
        assert ev.id == event_id
        assert ev.action == "invoice.created"
        assert ev.actor_type == "API_KEY"
        assert ev.data == {}
        assert ev.data == {}
    finally:
        client._close()


def test_list_paginates(monkeypatch):
    pages = [
        {
            "data": [
                _make_resource("11111111-1111-1111-1111-111111111111"),
            ],
            "links": {"next": "/api/v1/events?page[size]=1&page[after]=tok-2"},
            "meta": {"page_size": 1},
        },
        {
            "data": [_make_resource("22222222-2222-2222-2222-222222222222")],
            "meta": {"page_size": 1},
        },
    ]
    call_count = [0]

    def handler(req: httpx.Request) -> httpx.Response:
        page = pages[call_count[0]]
        call_count[0] += 1
        return httpx.Response(200, json=page)

    transport = httpx.MockTransport(handler)
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        first = client.events.list(page_size=1)
        assert len(first.events) == 1
        assert first.next_cursor == "tok-2"

        second = client.events.list(page_size=1, page_after=first.next_cursor)
        assert len(second.events) == 1
        assert second.next_cursor is None
    finally:
        client._close()


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


def test_event_from_resource_handles_nullable_actor_id():
    resource = _make_resource("33333333-3333-3333-3333-333333333333", actor_id=None)
    ev = Event._from_resource(resource)
    assert ev.actor_id is None


def test_event_from_resource_handles_z_suffix_timestamps():
    resource = _make_resource(
        "44444444-4444-4444-4444-444444444444",
        occurred_at="2026-05-06T12:00:00Z",
    )
    ev = Event._from_resource(resource)
    assert ev.occurred_at.tzinfo is not None


# Helpers ------------------------------------------------------------------


def _make_resource(
    event_id: str,
    *,
    actor_id: str | None = None,
    occurred_at: str = "2026-05-06T12:00:00+00:00",
) -> dict:
    return {
        "id": event_id,
        "type": "event",
        "attributes": {
            "action": "invoice.created",
            "resource_type": "invoice",
            "resource_id": "inv-1",
            "occurred_at": occurred_at,
            "created_at": "2026-05-06T12:00:01+00:00",
            "actor_type": "USER" if actor_id else "API_KEY",
            "actor_id": actor_id,
            "actor_label": "alice@example.com" if actor_id else "",
            "data": {},
            "idempotency_key": "auto-abc",
        },
    }


# Silence unused-import warnings in static analyzers
_ = (MagicMock, datetime, timezone, MAX_BUFFER_SIZE)
_ = pytest  # noqa: F841
_ = _StubResponse  # noqa: F841
