"""Audit namespace clients (sync + async).

Public surface:

    client.audit.events.record(action, resource_type, resource_id, ...)
    client.audit.events.list(...)
    client.audit.events.get(event_id)

    client.audit.resource_types.list(...)
    client.audit.actions.list(filter_resource_type=None, ...)

    client.audit.forwarders.create(name, forwarder_type, http, ...)
    client.audit.forwarders.list(...)
    client.audit.forwarders.get(forwarder_id)
    client.audit.forwarders.update(forwarder_id, ...)
    client.audit.forwarders.delete(forwarder_id)
    client.audit.forwarders.deliveries.list(forwarder_id, ...)
    client.audit.forwarders.deliveries.actions.retry(forwarder_id, delivery_id)
    client.audit.forwarders.actions.retry_failed_deliveries(forwarder_id)
    client.audit.functions.test_forwarder.actions.execute(...)
    client.audit.functions.wipe.actions.execute()

ADR-047 §2.7. ``record`` is fire-and-forget by default — it enqueues
the event onto an in-memory bounded buffer (``smplkit.audit._buffer``)
and returns immediately; the buffer's worker thread retries with
exponential backoff on transient failures and drops oldest under back
pressure. Reads (``list``, ``get``) and forwarder management are
synchronous.

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
from smplkit._generated.audit.api.functions import (
    execute_wipe as _gen_execute_wipe,
)
from smplkit._generated.audit.api.resource_types import (
    list_actions as _gen_list_actions,
    list_resource_types as _gen_list_resource_types,
)
from smplkit._generated.audit.api.forwarders import (
    create_forwarder as _gen_create_forwarder,
    delete_forwarder as _gen_delete_forwarder,
    execute_test_forwarder as _gen_execute_test_forwarder,
    get_forwarder as _gen_get_forwarder,
    list_forwarder_deliveries as _gen_list_forwarder_deliveries,
    list_forwarders as _gen_list_forwarders,
    retry_failed_forwarder_deliveries as _gen_retry_failed_forwarder_deliveries,
    retry_forwarder_delivery as _gen_retry_forwarder_delivery,
    update_forwarder as _gen_update_forwarder,
)
from smplkit._generated.audit.client import AuthenticatedClient
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit._generated.audit.models.event import Event as _GenEvent
from smplkit._generated.audit.models.event_data import EventData as _GenEventData
from smplkit._generated.audit.models.event_resource import EventResource as _GenEventResource
from smplkit._generated.audit.models.event_response import EventResponse as _GenEventResponse
from smplkit._generated.audit.models.forwarder import Forwarder as _GenForwarder
from smplkit._generated.audit.models.forwarder_data import ForwarderData as _GenForwarderData
from smplkit._generated.audit.models.forwarder_filter_type_0 import (
    ForwarderFilterType0 as _GenForwarderFilter,
)
from smplkit._generated.audit.models.forwarder_http import ForwarderHttp as _GenForwarderHttp
from smplkit._generated.audit.models.forwarder_resource import (
    ForwarderResource as _GenForwarderResource,
)
from smplkit._generated.audit.models.forwarder_response import (
    ForwarderResponse as _GenForwarderResponse,
)
from smplkit._generated.audit.models.http_header import HttpHeader as _GenHttpHeader
from smplkit._generated.audit.models.test_forwarder_request import (
    TestForwarderRequest as _GenTestForwarderRequest,
)
from smplkit._generated.audit.models.wipe_request import (
    WipeRequest as _GenWipeRequest,
)
from smplkit._generated.audit.types import UNSET
from smplkit.audit._buffer import AuditEventBuffer, _PendingEvent
from smplkit.audit.models import (
    Action,
    Event,
    Forwarder,
    ForwarderDelivery,
    ForwarderHttp,
    HttpHeader,
    ResourceType,
    RetryFailedDeliveriesSummary,
    TestForwarderResult,
    WipeResult,
)

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


# ---------------------------------------------------------------------------
# Forwarders
# ---------------------------------------------------------------------------


def _http_to_gen(http: ForwarderHttp | dict[str, Any]) -> _GenForwarderHttp:
    """Convert a wrapper ForwarderHttp (or its dict equivalent) to the
    typed generated model. Going through the typed constructor means a
    spec change that drops a field will fail to compile here, instead
    of silently passing through on the wire."""
    src = http._to_dict() if isinstance(http, ForwarderHttp) else dict(http)
    headers = [_GenHttpHeader(name=h["name"], value=h["value"]) for h in (src.get("headers") or [])]
    return _GenForwarderHttp(
        url=src["url"],
        method=src.get("method", "POST"),
        headers=headers,
        body=src.get("body"),
        success_status=src.get("success_status", "2xx"),
    )


def _build_forwarder_attrs(
    *,
    name: str,
    forwarder_type: str,
    http: ForwarderHttp | dict[str, Any],
    enabled: bool,
    filter: dict[str, Any] | None,
    transform: str | None,
    data: dict[str, Any] | None,
) -> _GenForwarder:
    attrs = _GenForwarder(
        name=name,
        forwarder_type=forwarder_type,
        http=_http_to_gen(http),
        enabled=enabled,
    )
    if filter is not None:
        attrs.filter_ = _GenForwarderFilter.from_dict(filter)
    if transform is not None:
        attrs.transform = transform
    if data is not None:
        attrs.data = _GenForwarderData.from_dict(data)
    return attrs


def _expect_status(resp: Any, *expected: int) -> None:
    if resp.status_code not in expected or resp.parsed is None:
        raise UnexpectedStatus(resp.status_code, resp.content)


class _DeliveryActionsClient:
    """Surface for ``client.audit.forwarders.deliveries.actions.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

    def retry(
        self,
        forwarder_id: UUID | str,
        delivery_id: UUID | str,
    ) -> ForwarderDelivery:
        """Retry a single failed delivery.

        Records a new ``forwarder_delivery`` row with attempt_number =
        prior + 1; the prior row is unchanged. Returns the new row.
        """
        fid = forwarder_id if isinstance(forwarder_id, UUID) else UUID(str(forwarder_id))
        did = delivery_id if isinstance(delivery_id, UUID) else UUID(str(delivery_id))
        resp = _gen_retry_forwarder_delivery.sync_detailed(forwarder_id=fid, delivery_id=did, client=self._auth)
        _expect_status(resp, 200)
        return ForwarderDelivery._from_resource(resp.parsed.to_dict()["data"])


class _DeliveriesClient:
    """Surface for ``client.audit.forwarders.deliveries.*``."""

    actions: _DeliveryActionsClient

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client
        self.actions = _DeliveryActionsClient(auth_client=auth_client)

    def list(
        self,
        forwarder_id: UUID | str,
        *,
        status: str | None = None,
        created_at_range: str | None = None,
        page_size: int | None = None,
        page_after: str | None = None,
    ) -> "DeliveryListPage":
        """List delivery rows for a forwarder.

        Filters and pagination follow the same conventions as the events
        list endpoint. ``status`` is one of ``succeeded`` / ``failed`` /
        ``filtered_out`` / ``skipped_do_not_forward``;
        ``created_at_range`` uses the platform's interval notation
        (``[2026-01-01T00:00:00Z,*)``).
        """
        fid = forwarder_id if isinstance(forwarder_id, UUID) else UUID(str(forwarder_id))
        resp = _gen_list_forwarder_deliveries.sync_detailed(
            forwarder_id=fid,
            client=self._auth,
            filterstatus=status if status is not None else UNSET,
            filtercreated_at=created_at_range if created_at_range is not None else UNSET,
            pagesize=page_size if page_size is not None else UNSET,
            pageafter=page_after if page_after is not None else UNSET,
        )
        _expect_status(resp, 200)
        body_dict = resp.parsed.to_dict()
        deliveries = [ForwarderDelivery._from_resource(r) for r in body_dict.get("data", [])]
        next_link = (body_dict.get("links") or {}).get("next")
        next_cursor = None
        if next_link and "page[after]=" in next_link:
            next_cursor = next_link.split("page[after]=", 1)[1]
        return DeliveryListPage(deliveries=deliveries, next_cursor=next_cursor)


class _ForwarderActionsClient:
    """Surface for ``client.audit.forwarders.actions.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

    def retry_failed_deliveries(self, forwarder_id: UUID | str) -> RetryFailedDeliveriesSummary:
        """Retry every failed delivery for a forwarder.

        Returns a summary ``{attempted, succeeded, failed}`` reflecting
        the outcomes of the new attempts.
        """
        fid = forwarder_id if isinstance(forwarder_id, UUID) else UUID(str(forwarder_id))
        resp = _gen_retry_failed_forwarder_deliveries.sync_detailed(forwarder_id=fid, client=self._auth)
        _expect_status(resp, 200)
        d = resp.parsed.to_dict()
        return RetryFailedDeliveriesSummary(
            attempted=int(d.get("attempted") or 0),
            succeeded=int(d.get("succeeded") or 0),
            failed=int(d.get("failed") or 0),
        )


class _ForwardersClient:
    """Surface for ``client.audit.forwarders.*``."""

    deliveries: _DeliveriesClient
    actions: _ForwarderActionsClient

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client
        self.deliveries = _DeliveriesClient(auth_client=auth_client)
        self.actions = _ForwarderActionsClient(auth_client=auth_client)

    def create(
        self,
        *,
        name: str,
        forwarder_type: str,
        http: ForwarderHttp | dict[str, Any],
        enabled: bool = True,
        filter: dict[str, Any] | None = None,
        transform: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Forwarder:
        """Create a forwarder.

        Args:
            name: Display name. The slug is derived server-side.
            forwarder_type: One of ``http``, ``datadog``, ``splunk_hec``,
                ``sumo_logic``, ``new_relic``, ``honeycomb``, ``elastic``.
            http: Destination configuration. Headers carry credentials
                and are encrypted at rest server-side; reads return them
                redacted.
            enabled: Whether the forwarder is active. Defaults true.
            filter: Optional JSON Logic filter; events that don't match
                are recorded as ``filtered_out`` deliveries.
            transform: Optional JSONata template applied to the event
                payload before POST. Empty/None sends the event as-is.
            data: Free-form attributes JSON.
        """
        attrs = _build_forwarder_attrs(
            name=name,
            forwarder_type=forwarder_type,
            http=http,
            enabled=enabled,
            filter=filter,
            transform=transform,
            data=data,
        )
        body = _GenForwarderResponse(data=_GenForwarderResource(id="", attributes=attrs))
        resp = _gen_create_forwarder.sync_detailed(client=self._auth, body=body)
        _expect_status(resp, 201)
        return Forwarder._from_resource(resp.parsed.to_dict()["data"])

    def list(
        self,
        *,
        forwarder_type: str | None = None,
        enabled: bool | None = None,
        page_size: int | None = None,
        page_after: str | None = None,
    ) -> "ForwarderListPage":
        """List forwarders for the authenticated account."""
        resp = _gen_list_forwarders.sync_detailed(
            client=self._auth,
            filterforwarder_type=forwarder_type if forwarder_type is not None else UNSET,
            filterenabled=enabled if enabled is not None else UNSET,
            pagesize=page_size if page_size is not None else UNSET,
            pageafter=page_after if page_after is not None else UNSET,
        )
        _expect_status(resp, 200)
        body_dict = resp.parsed.to_dict()
        forwarders = [Forwarder._from_resource(r) for r in body_dict.get("data", [])]
        next_link = (body_dict.get("links") or {}).get("next")
        next_cursor = None
        if next_link and "page[after]=" in next_link:
            next_cursor = next_link.split("page[after]=", 1)[1]
        return ForwarderListPage(forwarders=forwarders, next_cursor=next_cursor)

    def get(self, forwarder_id: UUID | str) -> Forwarder:
        fid = forwarder_id if isinstance(forwarder_id, UUID) else UUID(str(forwarder_id))
        resp = _gen_get_forwarder.sync_detailed(forwarder_id=fid, client=self._auth)
        _expect_status(resp, 200)
        return Forwarder._from_resource(resp.parsed.to_dict()["data"])

    def update(
        self,
        forwarder_id: UUID | str,
        *,
        name: str,
        forwarder_type: str,
        http: ForwarderHttp | dict[str, Any],
        enabled: bool = True,
        filter: dict[str, Any] | None = None,
        transform: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Forwarder:
        """Full-replace update. PUT semantics — every field is overwritten.

        Header values must be re-supplied as plaintext; the GET path
        redacts them, so a PUT body containing ``"<redacted>"`` would
        persist that literal. Track real header values client-side and
        round-trip them on update.
        """
        fid = forwarder_id if isinstance(forwarder_id, UUID) else UUID(str(forwarder_id))
        attrs = _build_forwarder_attrs(
            name=name,
            forwarder_type=forwarder_type,
            http=http,
            enabled=enabled,
            filter=filter,
            transform=transform,
            data=data,
        )
        body = _GenForwarderResponse(data=_GenForwarderResource(id=str(fid), attributes=attrs))
        resp = _gen_update_forwarder.sync_detailed(forwarder_id=fid, client=self._auth, body=body)
        _expect_status(resp, 200)
        return Forwarder._from_resource(resp.parsed.to_dict()["data"])

    def delete(self, forwarder_id: UUID | str) -> None:
        """Soft-delete a forwarder."""
        fid = forwarder_id if isinstance(forwarder_id, UUID) else UUID(str(forwarder_id))
        resp = _gen_delete_forwarder.sync_detailed(forwarder_id=fid, client=self._auth)
        if resp.status_code != 204:
            raise UnexpectedStatus(resp.status_code, resp.content)


class ForwarderListPage:
    """A single page from ``client.audit.forwarders.list(...)``."""

    __slots__ = ("forwarders", "next_cursor")

    def __init__(self, *, forwarders: list[Forwarder], next_cursor: str | None) -> None:
        self.forwarders = forwarders
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self.forwarders)

    def __len__(self) -> int:
        return len(self.forwarders)


class DeliveryListPage:
    """A single page from ``client.audit.forwarders.deliveries.list(...)``."""

    __slots__ = ("deliveries", "next_cursor")

    def __init__(self, *, deliveries: list[ForwarderDelivery], next_cursor: str | None) -> None:
        self.deliveries = deliveries
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self.deliveries)

    def __len__(self) -> int:
        return len(self.deliveries)


# ---------------------------------------------------------------------------
# functions.test_forwarder
# ---------------------------------------------------------------------------


class _TestForwarderActionsClient:
    """Surface for ``client.audit.functions.test_forwarder.actions.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

    def execute(
        self,
        *,
        url: str,
        method: str = "POST",
        headers: list[HttpHeader] | list[dict[str, str]] | None = None,
        body: str | None = None,
        success_status: str = "2xx",
        timeout_ms: int | None = None,
    ) -> TestForwarderResult:
        """Server-side proxy to a customer-supplied URL.

        Exists to bypass browser CORS in the console's "try it out"
        button. SSRF-guarded server-side: private/loopback/link-local
        addresses (incl. the EC2 IMDS at 169.254.169.254) and ports
        outside the allowlist are rejected without making the request.
        """
        gen_headers: list[_GenHttpHeader] = []
        for h in headers or []:
            if isinstance(h, HttpHeader):
                gen_headers.append(_GenHttpHeader(name=h.name, value=h.value))
            else:
                gen_headers.append(_GenHttpHeader(name=h["name"], value=h["value"]))

        gen_body = _GenTestForwarderRequest(
            url=url,
            method=method,
            headers=gen_headers,
            body=body,
            success_status=success_status,
        )
        if timeout_ms is not None:
            gen_body.timeout_ms = timeout_ms
        resp = _gen_execute_test_forwarder.sync_detailed(client=self._auth, body=gen_body)
        _expect_status(resp, 200)
        d = resp.parsed.to_dict()
        return TestForwarderResult(
            succeeded=bool(d.get("succeeded")),
            response_status=d.get("response_status"),
            response_headers=dict(d.get("response_headers") or {}),
            response_body=str(d.get("response_body") or ""),
            latency_ms=d.get("latency_ms"),
            error=d.get("error"),
        )


class _TestForwarderClient:
    """Surface for ``client.audit.functions.test_forwarder.*``."""

    actions: _TestForwarderActionsClient

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self.actions = _TestForwarderActionsClient(auth_client=auth_client)


class _WipeActionsClient:
    """Surface for ``client.audit.functions.wipe.actions.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

    def execute(self) -> WipeResult:
        """Wipe every audit-database row scoped to the authenticated account.

        Atomic within the audit database — either every account-scoped row
        is gone, or none is. Returns the per-table delete counts so callers
        can surface the breakdown in logs or UX. ADR-047 §2.14.

        v1 RBAC posture: any valid credential (customer API key or browser
        JWT) may call this. Future RBAC ADRs may narrow the surface.
        """
        body = _GenWipeRequest()
        resp = _gen_execute_wipe.sync_detailed(client=self._auth, body=body)
        _expect_status(resp, 200)
        return WipeResult._from_response(resp.parsed.to_dict())


class _WipeClient:
    """Surface for ``client.audit.functions.wipe.*``."""

    actions: _WipeActionsClient

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self.actions = _WipeActionsClient(auth_client=auth_client)


class _FunctionsClient:
    """Surface for ``client.audit.functions.*``."""

    test_forwarder: _TestForwarderClient
    wipe: _WipeClient

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self.test_forwarder = _TestForwarderClient(auth_client=auth_client)
        self.wipe = _WipeClient(auth_client=auth_client)


# ---------------------------------------------------------------------------
# resource_types and actions — distinct-value side tables backing the
# Activity tab filter dropdowns. ADR-047 §2.5.
# ---------------------------------------------------------------------------


class ResourceTypeListPage:
    """A single page from ``client.audit.resource_types.list(...)``."""

    __slots__ = ("resource_types", "next_cursor")

    def __init__(self, *, resource_types: list[ResourceType], next_cursor: str | None) -> None:
        self.resource_types = resource_types
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self.resource_types)

    def __len__(self) -> int:
        return len(self.resource_types)


class ActionListPage:
    """A single page from ``client.audit.actions.list(...)``."""

    __slots__ = ("actions", "next_cursor")

    def __init__(self, *, actions: list[Action], next_cursor: str | None) -> None:
        self.actions = actions
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self.actions)

    def __len__(self) -> int:
        return len(self.actions)


def _extract_next_cursor(body_dict: dict[str, Any]) -> str | None:
    next_link = (body_dict.get("links") or {}).get("next")
    if next_link and "page[after]=" in next_link:
        # The link may include other query params after the cursor; the
        # cursor token is base64-url-safe so we slice at the next ``&``.
        after = next_link.split("page[after]=", 1)[1]
        return after.split("&", 1)[0]
    return None


class _ResourceTypesClient:
    """Surface for ``client.audit.resource_types.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

    def list(
        self,
        *,
        page_size: int | None = None,
        page_after: str | None = None,
    ) -> ResourceTypeListPage:
        """List the distinct ``resource_type`` slugs seen in the account.

        Backed by a maintain-by-write side table (ADR-047 §2.5), so the
        response time is independent of how many years of events the
        account has accumulated. Sorted alphabetically; cursor pagination
        via ``page_after``.
        """
        resp = _gen_list_resource_types.sync_detailed(
            client=self._auth,
            pagesize=page_size if page_size is not None else UNSET,
            pageafter=page_after if page_after is not None else UNSET,
        )
        _expect_status(resp, 200)
        body_dict = resp.parsed.to_dict()
        rows = [ResourceType._from_resource(r) for r in body_dict.get("data", [])]
        return ResourceTypeListPage(
            resource_types=rows, next_cursor=_extract_next_cursor(body_dict)
        )


class _ActionsClient:
    """Surface for ``client.audit.actions.*``."""

    def __init__(self, *, auth_client: AuthenticatedClient) -> None:
        self._auth = auth_client

    def list(
        self,
        *,
        filter_resource_type: str | None = None,
        page_size: int | None = None,
        page_after: str | None = None,
    ) -> ActionListPage:
        """List the distinct ``action`` slugs seen in the account.

        Without ``filter_resource_type``, returns one row per distinct
        action — an action recorded with multiple resource_types appears
        once. With the filter, returns the actions seen with that
        specific resource_type, powering the cascading-filter behavior
        on the Activity tab.

        ADR-047 §2.5. Sorted alphabetically; cursor pagination via
        ``page_after``.
        """
        resp = _gen_list_actions.sync_detailed(
            client=self._auth,
            filterresource_type=(
                filter_resource_type if filter_resource_type is not None else UNSET
            ),
            pagesize=page_size if page_size is not None else UNSET,
            pageafter=page_after if page_after is not None else UNSET,
        )
        _expect_status(resp, 200)
        body_dict = resp.parsed.to_dict()
        rows = [Action._from_resource(r) for r in body_dict.get("data", [])]
        return ActionListPage(
            actions=rows, next_cursor=_extract_next_cursor(body_dict)
        )


# ---------------------------------------------------------------------------
# Top-level audit clients
# ---------------------------------------------------------------------------


class AuditClient:
    """``client.audit.*`` synchronous surface."""

    events: _EventsClient
    resource_types: _ResourceTypesClient
    actions: _ActionsClient
    forwarders: _ForwardersClient
    functions: _FunctionsClient

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
        self.resource_types = _ResourceTypesClient(auth_client=self._auth)
        self.actions = _ActionsClient(auth_client=self._auth)
        self.forwarders = _ForwardersClient(auth_client=self._auth)
        self.functions = _FunctionsClient(auth_client=self._auth)

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
    resource_types: _ResourceTypesClient
    actions: _ActionsClient
    forwarders: _ForwardersClient
    functions: _FunctionsClient

    def __init__(self, *, api_key: str, base_url: str, extra_headers: dict[str, str] | None = None) -> None:
        self._inner = AuditClient(api_key=api_key, base_url=base_url, extra_headers=extra_headers)
        self.events = self._inner.events
        self.resource_types = self._inner.resource_types
        self.actions = self._inner.actions
        self.forwarders = self._inner.forwarders
        self.functions = self._inner.functions

    async def _close(self) -> None:
        self._inner._close()
