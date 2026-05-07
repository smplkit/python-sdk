"""Audit resource models exposed by the SDK.

The wrapper layer's domain types — ``Event``, ``Forwarder``,
``ForwarderHttp``, ``HttpHeader``, ``ForwarderDelivery``, plus the
plain-JSON ``TestForwarderResult`` — sit on top of the auto-generated
``smplkit._generated.audit.models``. The split keeps the public-facing
SDK surface stable across regenerations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Event:
    """A single audit event as returned by the audit service.

    ADR-047 §2.3.1. Field set mirrors the JSON:API resource attributes plus
    the resource ``id``.
    """

    id: UUID
    action: str
    resource_type: str
    resource_id: str
    actor_type: str
    actor_label: str
    occurred_at: datetime
    created_at: datetime
    actor_id: UUID | None = None
    snapshot: dict[str, Any] | None = None
    data: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""
    do_not_forward: bool = False

    @classmethod
    def _from_resource(cls, resource: dict[str, Any]) -> "Event":
        attrs = resource.get("attributes", {})
        actor_id = attrs.get("actor_id")
        return cls(
            id=UUID(resource["id"]),
            action=attrs["action"],
            resource_type=attrs["resource_type"],
            resource_id=attrs["resource_id"],
            actor_type=attrs.get("actor_type") or "",
            actor_label=attrs.get("actor_label") or "",
            actor_id=UUID(actor_id) if actor_id else None,
            occurred_at=_parse_iso(attrs["occurred_at"]),
            created_at=_parse_iso(attrs["created_at"]),
            snapshot=attrs.get("snapshot"),
            data=attrs.get("data") or {},
            idempotency_key=attrs.get("idempotency_key") or "",
            do_not_forward=bool(attrs.get("do_not_forward", False)),
        )


@dataclass(frozen=True, slots=True)
class HttpHeader:
    """A single name/value HTTP header on a forwarder destination."""

    name: str
    value: str

    def _to_dict(self) -> dict[str, str]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True, slots=True)
class ForwarderHttp:
    """Forwarder destination HTTP request shape.

    ``success_status`` is a 3-character string: either an exact code
    (``"200"``, ``"204"``) or a class (``"2xx"``, ``"4xx"``).
    """

    method: str = "POST"
    url: str = ""
    headers: list[HttpHeader] = field(default_factory=list)
    body: str | None = None
    success_status: str = "2xx"

    def _to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": [h._to_dict() for h in self.headers],
            "body": self.body,
            "success_status": self.success_status,
        }

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> "ForwarderHttp":
        return cls(
            method=raw.get("method") or "POST",
            url=raw.get("url") or "",
            headers=[HttpHeader(name=h.get("name", ""), value=h.get("value", "")) for h in raw.get("headers") or []],
            body=raw.get("body"),
            success_status=raw.get("success_status") or "2xx",
        )


@dataclass(frozen=True, slots=True)
class Forwarder:
    """A SIEM streaming forwarder configured on the customer's account.

    Header values from ``http.headers`` are always returned redacted on
    reads — the GET path on the audit API replaces every header value
    with ``"<redacted>"``. Re-supply the real values when calling
    ``update`` (the SDK does not cache them client-side).
    """

    id: UUID
    name: str
    slug: str
    forwarder_type: str
    enabled: bool
    http: ForwarderHttp
    filter: dict[str, Any] | None = None
    transform: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    version: int | None = None

    @classmethod
    def _from_resource(cls, resource: dict[str, Any]) -> "Forwarder":
        attrs = resource.get("attributes", {})
        return cls(
            id=UUID(resource["id"]),
            name=attrs.get("name") or "",
            slug=attrs.get("slug") or "",
            forwarder_type=attrs.get("forwarder_type") or "",
            enabled=bool(attrs.get("enabled", True)),
            filter=attrs.get("filter"),
            transform=attrs.get("transform"),
            http=ForwarderHttp._from_dict(attrs.get("http") or {}),
            data=attrs.get("data") or {},
            created_at=_parse_iso_or_none(attrs.get("created_at")),
            updated_at=_parse_iso_or_none(attrs.get("updated_at")),
            deleted_at=_parse_iso_or_none(attrs.get("deleted_at")),
            version=attrs.get("version"),
        )


@dataclass(frozen=True, slots=True)
class ForwarderDelivery:
    """One delivery attempt recorded by the forwarder loop.

    ``request.headers`` are stored redacted. ``status`` is one of
    ``"succeeded"``, ``"failed"``, ``"filtered_out"``, or
    ``"skipped_do_not_forward"``.
    """

    id: UUID
    forwarder_id: UUID
    event_id: UUID
    attempt_number: int
    status: str
    request: dict[str, Any] | None = None
    response_status: int | None = None
    response_body: str | None = None
    latency_ms: int | None = None
    error: str | None = None
    created_at: datetime | None = None

    @classmethod
    def _from_resource(cls, resource: dict[str, Any]) -> "ForwarderDelivery":
        attrs = resource.get("attributes", {})
        return cls(
            id=UUID(resource["id"]),
            forwarder_id=UUID(attrs["forwarder_id"]),
            event_id=UUID(attrs["event_id"]),
            attempt_number=int(attrs.get("attempt_number") or 1),
            status=attrs.get("status") or "",
            request=attrs.get("request"),
            response_status=attrs.get("response_status"),
            response_body=attrs.get("response_body"),
            latency_ms=attrs.get("latency_ms"),
            error=attrs.get("error"),
            created_at=_parse_iso_or_none(attrs.get("created_at")),
        )


@dataclass(frozen=True, slots=True)
class TestForwarderResult:
    """Plain-JSON response from ``functions.test_forwarder.actions.execute``.

    ``response_headers`` are echoed back unredacted — the caller already
    supplied the destination headers and the response is for them, not
    persisted to a delivery row.
    """

    # Pytest auto-collects classes whose name starts with "Test"; this
    # marker tells the collector to skip the dataclass.
    __test__ = False

    succeeded: bool
    response_status: int | None
    response_headers: dict[str, str]
    response_body: str
    latency_ms: int | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RetryFailedDeliveriesSummary:
    attempted: int
    succeeded: int
    failed: int


def _parse_iso(value: str) -> datetime:
    # Python's fromisoformat accepts an optional trailing 'Z' (treated as UTC)
    # in 3.11+. The audit service emits +00:00 anyway, but customers may pass
    # ``Z`` from JS-flavored timestamps.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _parse_iso_or_none(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_iso(value)
