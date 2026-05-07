"""Audit namespace clients (sync + async).

Public surface:

    client.audit.events.create(action, resource_type, resource_id, ...)
    client.audit.events.list(...)
    client.audit.events.get(event_id)

ADR-047 §2.6. ``create`` is fire-and-forget by default — it enqueues
the event onto an in-memory bounded buffer (``smplkit.audit._buffer``)
and returns immediately; the buffer's worker thread retries with
exponential backoff on transient failures and drops oldest under back
pressure. Reads (``list``, ``get``) are synchronous.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from smplkit.audit._buffer import AuditEventBuffer, _PendingEvent
from smplkit.audit.models import Event

logger = logging.getLogger("smplkit.audit")


def _build_attributes(
    action: str,
    resource_type: str,
    resource_id: str,
    *,
    occurred_at: datetime | None,
    snapshot: dict[str, Any] | None,
    data: dict[str, Any] | None,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    if occurred_at is not None:
        attrs["occurred_at"] = occurred_at.astimezone(timezone.utc).isoformat()
    if snapshot is not None:
        attrs["snapshot"] = snapshot
    if data is not None:
        attrs["data"] = data
    return attrs


class _EventsClient:
    """Surface for ``client.audit.events.*``."""

    def __init__(
        self,
        *,
        http: httpx.Client,
        base_url: str,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

        def _post(item: _PendingEvent) -> "httpx.Response | Exception":
            try:
                headers: dict[str, str] = {
                    "Content-Type": "application/vnd.api+json",
                    "Accept": "application/vnd.api+json",
                }
                if item.idempotency_key is not None:
                    headers["Idempotency-Key"] = item.idempotency_key
                return self._http.post(
                    f"{self._base_url}/api/v1/events",
                    headers=headers,
                    json=item.body,
                    timeout=10.0,
                )
            except httpx.HTTPError as exc:
                return exc

        self._buffer = AuditEventBuffer(post_fn=_post)

    def record(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        *,
        occurred_at: datetime | None = None,
        snapshot: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        """Enqueue an audit event for asynchronous delivery.

        Returns immediately. The actual POST is performed on a background
        thread with retry on transient failures.

        Args:
            action: ``{resource_type}.{verb}`` (e.g. ``"invoice.created"``).
            resource_type: The resource type acted on. Customer events
                must NOT use the ``smpl.`` prefix — that namespace is
                reserved for smplkit-emitted events and the server will
                reject customer attempts with a 403.
            resource_id: Identifier of the affected resource.
            occurred_at: When the event happened in the originating
                system. Defaults to ``now`` server-side if omitted.
            snapshot: Optional full state snapshot (for `*.created`,
                ``*.updated``, ``*.discovered`` per ADR-047 §2.5).
            data: Free-form contextual extras (request id, IP, etc.).
            idempotency_key: Optional caller-supplied idempotency key.
                If omitted, the server derives one from event content
                (account_id + action + resource_type + resource_id +
                occurred_at + snapshot).
        """
        body = {
            "data": {
                "type": "event",
                "attributes": _build_attributes(
                    action,
                    resource_type,
                    resource_id,
                    occurred_at=occurred_at,
                    snapshot=snapshot,
                    data=data,
                ),
            }
        }
        self._buffer.enqueue(body, idempotency_key=idempotency_key)

    def list(
        self,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_type: str | None = None,
        actor_id: UUID | str | None = None,
        occurred_at_range: str | None = None,
        page_size: int | None = None,
        page_after: str | None = None,
    ) -> "EventListPage":
        """List audit events for the authenticated account.

        Filters apply server-side per ADR-047 §4. Pagination uses an
        opaque cursor (``page_after``); the returned page exposes
        ``next_cursor`` if more pages are available.
        """
        params: dict[str, Any] = {}
        if action is not None:
            params["filter[action]"] = action
        if resource_type is not None:
            params["filter[resource_type]"] = resource_type
        if resource_id is not None:
            params["filter[resource_id]"] = resource_id
        if actor_type is not None:
            params["filter[actor_type]"] = actor_type
        if actor_id is not None:
            params["filter[actor_id]"] = str(actor_id)
        if occurred_at_range is not None:
            params["filter[occurred_at]"] = occurred_at_range
        if page_size is not None:
            params["page[size]"] = page_size
        if page_after is not None:
            params["page[after]"] = page_after

        resp = self._http.get(
            f"{self._base_url}/api/v1/events",
            params=params,
            headers={"Accept": "application/vnd.api+json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        body = resp.json()
        events = [Event._from_resource(r) for r in body.get("data", [])]
        next_link = (body.get("links") or {}).get("next")
        next_cursor = None
        if next_link and "page[after]=" in next_link:
            next_cursor = next_link.split("page[after]=", 1)[1]
        return EventListPage(events=events, next_cursor=next_cursor)

    def get(self, event_id: UUID | str) -> Event:
        """Retrieve a single audit event by id.

        Raises ``httpx.HTTPStatusError`` on 404 if no event with that
        id exists in the caller's account.
        """
        resp = self._http.get(
            f"{self._base_url}/api/v1/events/{event_id}",
            headers={"Accept": "application/vnd.api+json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return Event._from_resource(resp.json()["data"])

    def flush(self, timeout: float | None = 5.0) -> None:
        """Block until the in-memory buffer is drained or ``timeout`` elapses."""
        self._buffer.flush(timeout=timeout)

    def _close(self) -> None:
        self._buffer.close()


class EventListPage:
    """A single page from ``client.audit.events.list(...)``.

    ``events`` is the page's events; ``next_cursor`` is the opaque token
    for the next page (or None when this is the last page).
    """

    __slots__ = ("events", "next_cursor")

    def __init__(self, *, events: list[Event], next_cursor: str | None) -> None:
        self.events = events
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)


class AuditClient:
    """``client.audit.*`` synchronous surface."""

    events: _EventsClient

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        self.events = _EventsClient(http=self._http, base_url=base_url)

    def _close(self) -> None:
        try:
            self.events._close()
        finally:
            self._http.close()


class AsyncAuditClient:
    """Placeholder async surface — currently delegates to the sync client.

    Full async support uses ``httpx.AsyncClient`` and an asyncio task
    per pending emit; that work is deferred to a follow-up because the
    primary smpl audit consumers (FastAPI request handlers, Django
    views, framework middleware) are mostly sync code today.
    """

    events: _EventsClient

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._inner = AuditClient(api_key=api_key, base_url=base_url)
        self.events = self._inner.events

    async def _close(self) -> None:
        self._inner._close()
