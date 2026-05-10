"""Audit runtime client.

Public surface (runtime):

    client.audit.events.record(action, resource_type, resource_id, ..., flush=False)
    client.audit.events.flush(timeout=5.0)

The runtime audit client is for fire-and-forget event recording in app
code. Every other audit-service operation — query, distinct-value
listings, forwarder CRUD, the test_forwarder action, the wipe action —
lives on :class:`smplkit.SmplManagementClient` under ``mgmt.audit.*``.
ADR-047 §2.7.

By default ``record`` enqueues onto an in-memory bounded buffer
(``smplkit.audit._buffer``) and returns immediately; the buffer's
worker thread retries with exponential backoff on transient failures
and drops the oldest item under back pressure. Pass ``flush=True``
when the caller needs the event durable before continuing — typically
in CLI tools, in-test assertions, or any flow about to terminate the
process.

All HTTP work is delegated to the auto-generated low-level client
under ``smplkit._generated.audit`` — the wrapper does not issue raw
HTTP requests.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from smplkit._generated.audit.api.events import (
    record_event as _gen_record_event,
)
from smplkit._generated.audit.client import AuthenticatedClient
from smplkit._generated.audit.models.event import Event as _GenEvent
from smplkit._generated.audit.models.event_data import EventData as _GenEventData
from smplkit._generated.audit.models.event_resource import EventResource as _GenEventResource
from smplkit._generated.audit.models.event_response import EventResponse as _GenEventResponse
from smplkit._generated.audit.types import UNSET
from smplkit.audit._buffer import AuditEventBuffer, _PendingEvent

logger = logging.getLogger("smplkit.audit")


class _EventsClient:
    """Surface for ``client.audit.events.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

        def _post(item: _PendingEvent) -> "int | Exception":
            try:
                idem = item.idempotency_key if item.idempotency_key is not None else UNSET
                resp = _gen_record_event.sync_detailed(
                    client=self._auth,
                    body=item.body,
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
        data: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        do_not_forward: bool = False,
        flush: bool = False,
        flush_timeout: float | None = 5.0,
    ) -> None:
        """Enqueue an audit event for asynchronous delivery.

        Returns immediately when ``flush`` is False (the default) — the
        buffer's worker thread performs the actual POST with retry on
        transient failures.

        When ``flush=True``, this call blocks until the buffer has
        drained or ``flush_timeout`` elapses. Use this when the caller
        needs the event durable before continuing — typical examples
        are CLI tools, in-test assertions, and any flow about to exit
        the process. The fire-and-forget default remains the right
        choice on the request-handling hot path.

        Args:
            action: ``{resource_type}.{verb}`` (e.g. ``"invoice.created"``).
            resource_type: The resource type acted on. Customer events
                must NOT use the ``smpl.`` prefix — that namespace is
                reserved for smplkit-emitted events and the server will
                reject customer attempts with a 403.
            resource_id: Identifier of the affected resource.
            occurred_at: When the event happened in the originating
                system. Defaults to ``now`` server-side if omitted.
            data: Free-form contextual JSON. To record a resource
                snapshot, place it inside ``data`` -- smplkit's internal
                convention nests it at ``data["snapshot"]`` for
                consistency with the platform's own emissions, but the
                shape is unconstrained::

                    record(
                        "invoice.created", "invoice", "inv-1",
                        data={"snapshot": {"total_cents": 4900}, "ip": "1.2.3.4"},
                    )

            idempotency_key: Optional caller-supplied idempotency key.
                If omitted, the server derives one from event content
                (account_id + action + resource_type + resource_id +
                occurred_at + data).
            do_not_forward: When True, the audit service records the
                event normally but does NOT POST it through any
                configured SIEM forwarder. A
                ``skipped_do_not_forward`` delivery row is recorded for
                each enabled forwarder so the skip is visible in the
                forwarder delivery log.
            flush: When True, block until the buffer drains (or
                ``flush_timeout`` elapses) before returning.
            flush_timeout: Upper bound on the blocking flush, in seconds.
                Ignored when ``flush`` is False. ``None`` blocks
                indefinitely.
        """
        attrs = _GenEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        if occurred_at is not None:
            attrs.occurred_at = occurred_at.astimezone(timezone.utc)
        if data is not None:
            attrs.data = _GenEventData.from_dict(data)
        if do_not_forward:
            attrs.do_not_forward = True
        body = _GenEventResponse(
            data=_GenEventResource(id="", attributes=attrs),
        )
        self._buffer.enqueue(body, idempotency_key=idempotency_key)
        if flush:
            self._buffer.flush(timeout=flush_timeout)

    def flush(self, timeout: float | None = 5.0) -> None:
        """Block until the in-memory buffer is drained or ``timeout`` elapses.

        Equivalent to passing ``flush=True`` to a final
        :meth:`record` call. Useful for draining buffered events at
        process shutdown or after a batch of fire-and-forget records.
        """
        self._buffer.flush(timeout=timeout)

    def _close(self) -> None:
        self._buffer.close()


class AuditClient:
    """``client.audit.*`` synchronous runtime surface.

    Constructed by :class:`smplkit.SmplClient`; not intended for direct
    instantiation.
    """

    events: _EventsClient

    def __init__(self, *, api_key: str, base_url: str, extra_headers: dict[str, str] | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._auth = AuthenticatedClient(
            base_url=self._base_url,
            token=api_key,
            timeout=httpx.Timeout(10.0),
            headers={**(extra_headers or {}), "Accept": "application/vnd.api+json"},
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
    """``client.audit.*`` async runtime surface — currently delegates to
    the sync client.

    Full async support uses ``httpx.AsyncClient`` and an asyncio task
    per pending emit; that work is deferred to a follow-up because the
    primary smpl audit consumers (FastAPI request handlers, Django
    views, framework middleware) are mostly sync code today.
    """

    events: _EventsClient

    def __init__(self, *, api_key: str, base_url: str, extra_headers: dict[str, str] | None = None) -> None:
        self._inner = AuditClient(api_key=api_key, base_url=base_url, extra_headers=extra_headers)
        self.events = self._inner.events

    async def _close(self) -> None:
        self._inner._close()
