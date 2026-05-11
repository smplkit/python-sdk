"""Smpl Audit management surface — ``mgmt.audit.*``.

Counterpart to the runtime :class:`smplkit.audit.AuditClient`. The
runtime client owns event recording and read-side queries; this client
owns SIEM forwarder CRUD:

* ``mgmt.audit.forwarders.create/get/list/update/delete`` — manage the
  customer's configured forwarders. Pro tier; gated on the
  ``audit.event_forwarding`` entitlement.

Async support mirrors the runtime audit client today: the
``AsyncAuditClient`` placeholder delegates to the sync surface so
async callers reach the same endpoints. Full asyncio_detailed wiring
is a follow-up; the contract on this module is stable regardless of
which transport powers it underneath.

New audit-management capabilities should add classes here, not in
``smplkit.audit.client``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from smplkit._generated.audit.api.forwarders import (
    create_forwarder as _gen_create_forwarder,
    delete_forwarder as _gen_delete_forwarder,
    get_forwarder as _gen_get_forwarder,
    list_forwarders as _gen_list_forwarders,
    update_forwarder as _gen_update_forwarder,
)
from smplkit._errors import Error as _SmplError, _raise_for_status
from smplkit._generated.audit.client import AuthenticatedClient as _AuditAuthClient
from smplkit._generated.audit.models.forwarder import Forwarder as _GenForwarder
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
from smplkit._generated.audit.types import UNSET
from smplkit.audit.models import (
    Forwarder,
    ForwarderHttp,
    ForwarderType,
)


def _expect_status(resp: Any, *expected: int) -> None:
    # The generated client raises JSONDecodeError for unparseable 2xx
    # bodies before we see them, so we only need to handle status-code
    # mismatches here. _raise_for_status maps 4xx/5xx to typed errors
    # (NotFoundError, PaymentRequiredError, ValidationError, ConflictError,
    # Error); a 2xx code the caller didn't expect falls through to the
    # defensive raise below.
    if resp.status_code not in expected:
        _raise_for_status(resp.status_code, resp.content)
        raise _SmplError(
            f"HTTP {resp.status_code} not among expected {expected}",
            status_code=resp.status_code,
        )


def _extract_next_cursor(body_dict: dict[str, Any]) -> str | None:
    next_link = (body_dict.get("links") or {}).get("next")
    if next_link and "page[after]=" in next_link:
        # The link may include other query params after the cursor; the
        # cursor token is base64-url-safe so we slice at the next ``&``.
        after = next_link.split("page[after]=", 1)[1]
        return after.split("&", 1)[0]
    return None


# ---------------------------------------------------------------------------
# Forwarders — CRUD
# ---------------------------------------------------------------------------


class ForwarderListPage:
    """A single page from ``mgmt.audit.forwarders.list(...)``."""

    __slots__ = ("forwarders", "next_cursor")

    def __init__(self, *, forwarders: list[Forwarder], next_cursor: str | None) -> None:
        self.forwarders = forwarders
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self.forwarders)

    def __len__(self) -> int:
        return len(self.forwarders)


def _http_to_gen(http: ForwarderHttp | dict[str, Any]) -> _GenForwarderHttp:
    """Convert a wrapper ForwarderHttp (or its dict equivalent) to the
    typed generated model. Going through the typed constructor means a
    spec change that drops a field will fail to compile here, instead of
    silently passing through on the wire."""
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
    forwarder_type: ForwarderType,
    http: ForwarderHttp | dict[str, Any],
    enabled: bool,
    filter: dict[str, Any] | None,
    transform: str | None,
) -> _GenForwarder:
    # ``ForwarderType`` is a ``str`` subclass — passing the enum directly
    # gives the generated model a string that matches its Literal type
    # constraint, while keeping enum identity for callers reading back.
    attrs = _GenForwarder(
        name=name,
        forwarder_type=ForwarderType(forwarder_type).value,
        http=_http_to_gen(http),
        enabled=enabled,
    )
    if filter is not None:
        attrs.filter_ = _GenForwarderFilter.from_dict(filter)
    if transform is not None:
        attrs.transform = transform
    return attrs


class ForwardersClient:
    """Surface for ``mgmt.audit.forwarders.*``."""

    def __init__(self, *, auth_client: _AuditAuthClient) -> None:
        self._auth = auth_client

    def create(
        self,
        *,
        name: str,
        forwarder_type: ForwarderType,
        http: ForwarderHttp | dict[str, Any],
        enabled: bool = True,
        filter: dict[str, Any] | None = None,
        transform: str | None = None,
    ) -> Forwarder:
        """Create a forwarder.

        Args:
            name: Display name. The slug is derived server-side.
            forwarder_type: A :class:`ForwarderType` enum member
                (e.g. ``ForwarderType.HTTP``, ``ForwarderType.DATADOG``).
                The constant is a ``str`` subclass, so callers passing
                the literal string (``"http"``) still type-check
                cleanly; the enum is the recommended form for IDE
                autocomplete and grep-ability.
            http: Destination configuration. Headers carry credentials
                and are encrypted at rest server-side; reads return them
                redacted.
            enabled: Whether the forwarder is active. Defaults true.
            filter: Optional JSON Logic filter; events that don't match
                are recorded as ``filtered_out`` deliveries.
            transform: Optional JSONata template applied to the event
                payload before POST. Empty/None sends the event as-is.
        """
        attrs = _build_forwarder_attrs(
            name=name,
            forwarder_type=forwarder_type,
            http=http,
            enabled=enabled,
            filter=filter,
            transform=transform,
        )
        body = _GenForwarderResponse(data=_GenForwarderResource(id="", attributes=attrs))
        resp = _gen_create_forwarder.sync_detailed(client=self._auth, body=body)
        _expect_status(resp, 201)
        return Forwarder._from_resource(resp.parsed.to_dict()["data"])

    def list(
        self,
        *,
        forwarder_type: ForwarderType | None = None,
        enabled: bool | None = None,
        page_size: int | None = None,
        page_after: str | None = None,
    ) -> ForwarderListPage:
        """List forwarders for the authenticated account."""
        ft = ForwarderType(forwarder_type).value if forwarder_type is not None else UNSET
        resp = _gen_list_forwarders.sync_detailed(
            client=self._auth,
            filterforwarder_type=ft,
            filterenabled=enabled if enabled is not None else UNSET,
            pagesize=page_size if page_size is not None else UNSET,
            pageafter=page_after if page_after is not None else UNSET,
        )
        _expect_status(resp, 200)
        body_dict = resp.parsed.to_dict()
        forwarders = [Forwarder._from_resource(r) for r in body_dict.get("data", [])]
        return ForwarderListPage(forwarders=forwarders, next_cursor=_extract_next_cursor(body_dict))

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
        forwarder_type: ForwarderType,
        http: ForwarderHttp | dict[str, Any],
        enabled: bool = True,
        filter: dict[str, Any] | None = None,
        transform: str | None = None,
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
            _raise_for_status(resp.status_code, resp.content)
            raise _SmplError(
                f"HTTP {resp.status_code} not 204",
                status_code=resp.status_code,
            )


# ---------------------------------------------------------------------------
# Top-level audit management clients
# ---------------------------------------------------------------------------


class AuditClient:
    """``mgmt.audit.*`` synchronous management surface.

    Constructed by :class:`smplkit.SmplManagementClient`; not intended
    for direct instantiation.
    """

    forwarders: ForwardersClient

    def __init__(self, *, auth_client: _AuditAuthClient) -> None:
        self._auth = auth_client
        self.forwarders = ForwardersClient(auth_client=auth_client)


class AsyncAuditClient:
    """``mgmt.audit.*`` async management surface.

    Today this delegates to the sync surface — the audit-service
    network calls are short and any awaitable wrapper is uncontroversial
    on top. Full ``asyncio_detailed`` plumbing is a follow-up; the
    contract on this client is stable regardless of which transport
    powers it underneath.
    """

    forwarders: ForwardersClient

    def __init__(self, *, auth_client: _AuditAuthClient) -> None:
        self._inner = AuditClient(auth_client=auth_client)
        self.forwarders = self._inner.forwarders


__all__ = [
    "AsyncAuditClient",
    "AuditClient",
    "ForwarderListPage",
    "ForwardersClient",
    "ForwarderType",
]
