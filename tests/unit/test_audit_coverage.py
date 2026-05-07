"""Coverage-targeted tests for the audit namespace.

Fills in branches that ``test_audit.py`` doesn't directly exercise so the
100% line-coverage gate stays green: list filter passthrough, get error
paths, AsyncAuditClient delegation, _build_attributes' optional snapshot
and data fields, and the buffer's gave-up + safe-body paths.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest

from smplkit.audit._buffer import (
    AuditEventBuffer,
    MAX_ATTEMPTS_PER_ITEM,
    _PendingEvent,
)
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit.audit.client import AsyncAuditClient, AuditClient


def test_buffer_enqueue_silent_when_closed() -> None:
    buf = AuditEventBuffer(post_fn=lambda item: 201)
    buf.close(timeout=1.0)
    # No-op: enqueue on a closed buffer just returns.
    buf.enqueue({"x": 1})


def test_buffer_flush_warns_on_timeout() -> None:
    """Hold one item in the queue and flush below the retry backoff."""
    attempts: list[int] = []

    def post(item: _PendingEvent) -> httpx.Response:
        attempts.append(item.attempts)
        return 503

    buf = AuditEventBuffer(post_fn=post, max_size=10, watermark=999)
    try:
        buf.enqueue({"i": 1})
        # Flush below the 250ms backoff so the queue stays non-empty.
        start = time.monotonic()
        buf.flush(timeout=0.05)
        assert time.monotonic() - start >= 0.04
    finally:
        buf.close(timeout=2.0)


def test_buffer_gives_up_after_max_attempts() -> None:
    attempts = [0]

    def post(item: _PendingEvent) -> httpx.Response:
        attempts[0] += 1
        return 503

    buf = AuditEventBuffer(
        post_fn=post,
        max_size=10,
        watermark=1,
        flush_interval=0.025,
    )
    try:
        buf.enqueue({"i": 1})
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if attempts[0] >= MAX_ATTEMPTS_PER_ITEM:
                break
            time.sleep(0.05)
        assert attempts[0] >= MAX_ATTEMPTS_PER_ITEM
    finally:
        buf.close(timeout=2.0)


def test_buffer_post_raising_treated_as_transient() -> None:
    calls = [0]

    def post(item: _PendingEvent):
        calls[0] += 1
        if calls[0] == 1:
            raise RuntimeError("simulated network blip")
        return 201

    buf = AuditEventBuffer(post_fn=post, max_size=10, watermark=1, flush_interval=0.05)
    try:
        buf.enqueue({"i": 1})
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if calls[0] >= 2:
                break
            time.sleep(0.05)
        assert calls[0] >= 2
    finally:
        buf.close(timeout=2.0)


# --------------------------------------------------------------------------
# AuditClient — branches not exercised in test_audit.py
# --------------------------------------------------------------------------


def test_create_serializes_snapshot_and_data() -> None:
    """Both snapshot and data fields are forwarded onto the request body."""
    import json as _json

    seen_bodies: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen_bodies.append(_json.loads(req.read()))
        return httpx.Response(
            201,
            json={
                "data": {
                    "id": "00000000-0000-0000-0000-000000000001",
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
                        "snapshot": None,
                        "data": {},
                        "idempotency_key": "k-1",
                    },
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        client.events.record(
            action="invoice.created",
            resource_type="invoice",
            resource_id="inv-1",
            occurred_at=datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
            snapshot={"total_cents": 4900},
            data={"request_id": "req-1"},
            idempotency_key="k-1",
        )
        client.events.flush(timeout=2.0)
        assert seen_bodies, "the buffer should have flushed at least one body"
        attrs = seen_bodies[0]["data"]["attributes"]
        assert attrs["snapshot"] == {"total_cents": 4900}
        assert attrs["data"] == {"request_id": "req-1"}
        assert attrs["occurred_at"].startswith("2026-05-06T12:00:00")
    finally:
        client._close()


def test_post_wrapper_returns_httpx_error_on_connection_failure() -> None:
    """Cover the audit client's POST-wrapper try/except (lines 80-81).

    A transport that raises httpx.ConnectError on every request forces
    the buffer's post wrapper into its except branch, where it returns
    the exception. The buffer reads it as transient and retries — we
    just need to assert at least one round-trip happened.
    """
    calls = [0]

    def handler(req: httpx.Request) -> httpx.Response:
        calls[0] += 1
        raise httpx.ConnectError("simulated connect failure")

    transport = httpx.MockTransport(handler)
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        client.events.record(action="x", resource_type="y", resource_id="1")
        # Force a drain pass via flush; the wrapper's except clause runs.
        client.events.flush(timeout=0.5)
        assert calls[0] >= 1
    finally:
        client._close()


def test_list_threads_filter_and_pagination_params() -> None:
    seen_urls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen_urls.append(str(req.url))
        return httpx.Response(200, json={"data": [], "links": {}, "meta": {"page_size": 50}})

    transport = httpx.MockTransport(handler)
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
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
    finally:
        client._close()


def test_list_raises_unexpected_status_on_5xx() -> None:
    """Cover the list path's UnexpectedStatus raise."""
    transport = httpx.MockTransport(lambda req: httpx.Response(503, json={}))
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        with pytest.raises(UnexpectedStatus):
            client.events.list()
    finally:
        client._close()


def test_get_raises_for_404() -> None:
    transport = httpx.MockTransport(lambda req: httpx.Response(404, json={}))
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        with pytest.raises(UnexpectedStatus):
            client.events.get(UUID("00000000-0000-0000-0000-000000000099"))
    finally:
        client._close()


def test_async_client_delegates_to_sync() -> None:
    """The current placeholder ``AsyncAuditClient`` re-exports the sync surface."""
    client = AsyncAuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    assert client.events is client._inner.events  # type: ignore[attr-defined]
    # The async close just delegates.
    import asyncio

    asyncio.run(client._close())


def test_event_list_page_iter_and_len() -> None:
    """The list-page object is iterable and supports len()."""
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "11111111-2222-3333-4444-555555555555",
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
                            "snapshot": None,
                            "data": {},
                            "idempotency_key": "k",
                        },
                    }
                ],
                "meta": {"page_size": 1},
            },
        )
    )
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    client._auth.set_httpx_client(httpx.Client(transport=transport, base_url="https://audit.example.com"))
    try:
        page = client.events.list()
        assert len(page) == 1
        ids = [e.id for e in page]
        assert ids[0] == UUID("11111111-2222-3333-4444-555555555555")
    finally:
        client._close()


def test_audit_client_extra_headers_reach_transport() -> None:
    """extra_headers are set as defaults on the underlying httpx.Client."""
    client = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com", extra_headers={"X-Test": "v"})
    http = client._auth.get_httpx_client()
    assert http.headers.get("x-test") == "v"
    client._close()


def test_async_audit_client_extra_headers_reach_transport() -> None:
    """AsyncAuditClient forwards extra_headers to its inner AuditClient."""
    client = AsyncAuditClient(api_key="sk_api_test", base_url="https://audit.example.com", extra_headers={"X-Test": "v"})
    http = client._inner._auth.get_httpx_client()
    assert http.headers.get("x-test") == "v"


_ = MagicMock  # silence unused-import warnings on aggressive linters
