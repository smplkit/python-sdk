"""Audit namespace clients (sync + async).

Public surface:

    client.audit.events.record(action, resource_type, resource_id, ...)
    client.audit.events.list(...)
    client.audit.events.get(event_id)

ADR-047 §2.6. ``record`` is fire-and-forget by default — it enqueues
the event onto an in-memory bounded buffer (``smplkit.audit._buffer``)
and returns immediately; the buffer's worker thread retries with
exponential backoff on transient failures and drops oldest under back
pressure. Reads (``list``, ``get``) are synchronous.

All HTTP work is delegated to the auto-generated low-level client
under ``smplkit._generated.audit`` — the wrapper does not issue raw
HTTP requests.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from smplkit._generated.audit.api.events import (
    get_event as _gen_get_event,
    list_events as _gen_list_events,
    record_event as _gen_record_event,
)
from smplkit._generated.audit.client import AuthenticatedClient
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit._generated.audit.models.event_response import EventResponse as _GenEventResponse
from smplkit._generated.audit.types import UNSET
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

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

        def _post(item: _PendingEvent) -> "int | Exception":
            try:
                gen_body = _GenEventResponse.from_dict(item.body)
                idem = item.idempotency_key if item.idempotency_key is not None else UNSET
                resp = _gen_record_event.sync_detailed(
                    client=self._auth,
                    body=gen_body,
                    idempotency_key=idem,
                )
                return resp.status_code
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
                "id": "",  # server assigns; required by the generated EventResource model
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
        actor_id_arg: Any = UNSET
        if actor_id is not None:
            actor_id_arg = actor_id if isinstance(actor_id, UUID) else UUID(str(actor_id))

        resp = _gen_list_events.sync_detailed(
            client=self._auth,
            filteraction=action if action is not None else UNSET,
            filterresource_type=resource_type if resource_type is not None else UNSET,
            filterresource_id=resource_id if resource_id is not None else UNSET,
            filteractor_type=actor_type if actor_type is not None else UNSET,
            filteractor_id=actor_id_arg,
            filteroccurred_at=occurred_at_range if occurred_at_range is not None else UNSET,
            pagesize=page_size if page_size is not None else UNSET,
            pageafter=page_after if page_after is not None else UNSET,
        )
        if resp.status_code != 200 or resp.parsed is None:
            raise UnexpectedStatus(resp.status_code, resp.content)

        body_dict = resp.parsed.to_dict()
        events = [Event._from_resource(r) for r in body_dict.get("data", [])]
        next_link = (body_dict.get("links") or {}).get("next")
        next_cursor = None
        if next_link and "page[after]=" in next_link:
            next_cursor = next_link.split("page[after]=", 1)[1]
        return EventListPage(events=events, next_cursor=next_cursor)

    def get(self, event_id: UUID | str) -> Event:
        """Retrieve a single audit event by id.

        Raises :class:`UnexpectedStatus` on non-2xx (404 if no event with
        that id exists in the caller's account).
        """
        eid = event_id if isinstance(event_id, UUID) else UUID(str(event_id))
        resp = _gen_get_event.sync_detailed(eid, client=self._auth)
        if resp.status_code != 200 or resp.parsed is None:
            raise UnexpectedStatus(resp.status_code, resp.content)
        return Event._from_resource(resp.parsed.to_dict()["data"])

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
        self._auth = AuthenticatedClient(
            base_url=self._base_url,
            token=api_key,
            timeout=httpx.Timeout(10.0),
            headers={"Accept": "application/vnd.api+json"},
        )
        self.events = _EventsClient(auth_client=self._auth)

    def _close(self) -> None:
        try:
            self.events._close()
        finally:
            try:
                self._auth.get_httpx_client().close()
            except Exception:  # pragma: no cover — close is best-effort
                pass


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
