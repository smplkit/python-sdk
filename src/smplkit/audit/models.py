"""Audit resource models exposed by the SDK.

The wrapper layer's domain types — ``Event``, ``Forwarder``,
``HttpConfiguration``, ``HttpHeader``, ``ResourceType``, ``Action`` —
sit on top of the auto-generated ``smplkit._generated.audit.models``.
The split keeps the public-facing SDK surface stable across
regenerations.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


class ForwarderType(str, enum.Enum):
    """Supported SIEM forwarder destination types.

    The audit service's OpenAPI spec declares ``forwarder_type`` as a
    string-with-enum-constraint (per ADR-047 §2.12); this Python-side
    Enum mirrors that constraint so customers get autocomplete and
    type-checked values instead of stringly-typed inputs. ``str``
    subclassing keeps interop with the auto-generated client transparent
    — a ``ForwarderType`` member compares equal to its string literal
    (``ForwarderType.HTTP == "HTTP"``).

    The available types are real-time HTTP destinations sharing one
    outbound plumbing path. Object-storage archival (S3, GCS, etc.) has
    different operational shape (batching, IAM, lifecycle policies) and
    will get its own type if customer demand warrants — see ADR-047
    §2.12.
    """

    DATADOG = "DATADOG"
    ELASTIC = "ELASTIC"
    HONEYCOMB = "HONEYCOMB"
    HTTP = "HTTP"
    NEW_RELIC = "NEW_RELIC"
    SPLUNK_HEC = "SPLUNK_HEC"
    SUMO_LOGIC = "SUMO_LOGIC"


class HttpMethod(str, enum.Enum):
    """HTTP verb used by a forwarder's outbound delivery.

    Mirrors the audit spec's ``HttpConfigurationMethod`` enum so
    customers get autocomplete and a typed value back from
    ``forwarder.configuration.method``. ``str`` subclassing keeps
    interop with raw strings transparent (``HttpMethod.POST == "POST"``).
    """

    DELETE = "DELETE"
    GET = "GET"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"


@dataclass(frozen=True, slots=True)
class Event:
    """A single audit event as returned by the audit service.

    ADR-047 §2.3.1. Field set mirrors the JSON:API resource attributes
    plus the resource ``id``.

    :ivar id: Server-assigned UUID for this event.
    :ivar action: Action slug — e.g. ``"user.created"``, ``"invoice.paid"``.
    :ivar resource_type: Type of resource the action operated on — e.g. ``"invoice"``.
    :ivar resource_id: Customer-facing id of the resource the action operated on.
    :ivar actor_type: Type of the actor that performed the action (``"user"``,
        ``"api_key"``, ``"system"``, …). Empty string when unknown.
    :ivar actor_label: Display label for the actor — typically a name or email.
        Empty string when unknown.
    :ivar occurred_at: When the action actually happened, as reported by the source.
    :ivar created_at: When the audit service first ingested this event.
    :ivar actor_id: UUID of the actor, when the actor is a tracked entity (user,
        api_key). ``None`` for system actors or anonymous events.
    :ivar data: Free-form per-event payload defined by the customer. Surfaced
        on the audit-event resource as a structured JSONB column.
    :ivar idempotency_key: Customer-supplied dedupe key. Empty when the customer
        didn't supply one.
    :ivar do_not_forward: When ``True``, skip this event from SIEM forwarder
        delivery regardless of any matching forwarder filter.
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
            data=attrs.get("data") or {},
            idempotency_key=attrs.get("idempotency_key") or "",
            do_not_forward=bool(attrs.get("do_not_forward", False)),
        )


@dataclass(frozen=True, slots=True)
class HttpHeader:
    """A single name/value HTTP header on a forwarder destination.

    :ivar name: Header name (e.g. ``"Authorization"``, ``"DD-API-KEY"``).
    :ivar value: Header value, plaintext on writes. The audit service encrypts
        values at rest; reads return them as ``"<redacted>"``.
    """

    name: str
    value: str

    def _to_dict(self) -> dict[str, str]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True, slots=True)
class HttpConfiguration:
    """Forwarder destination HTTP request shape.

    :ivar method: HTTP verb used for delivery. Defaults to ``HttpMethod.POST``.
    :ivar url: Destination URL the audit service POSTs each event to.
    :ivar headers: Headers attached to every outbound request. Values carry
        credentials and are encrypted at rest server-side; reads return them
        redacted.
    :ivar success_status: Status the destination must return for delivery to
        count as success — either an exact code (``"200"``, ``"204"``) or a
        class (``"2xx"``, ``"4xx"``). Defaults to ``"2xx"``.
    """

    method: HttpMethod = HttpMethod.POST
    url: str = ""
    headers: list[HttpHeader] = field(default_factory=list)
    success_status: str = "2xx"

    def _to_dict(self) -> dict[str, Any]:
        return {
            "method": HttpMethod(self.method).value,
            "url": self.url,
            "headers": [h._to_dict() for h in self.headers],
            "success_status": self.success_status,
        }

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> "HttpConfiguration":
        return cls(
            method=HttpMethod(raw.get("method") or HttpMethod.POST),
            url=raw.get("url") or "",
            headers=[HttpHeader(name=h.get("name", ""), value=h.get("value", "")) for h in raw.get("headers") or []],
            success_status=raw.get("success_status") or "2xx",
        )


@dataclass(frozen=True, slots=True)
class Forwarder:
    """A SIEM streaming forwarder configured on the customer's account.

    Header values from ``configuration.headers`` are always returned
    redacted on reads — the GET path on the audit API replaces every
    header value with ``"<redacted>"``. Re-supply the real values when
    calling ``update`` (the SDK does not cache them client-side).

    :ivar id: Server-assigned UUID for this forwarder.
    :ivar name: Display name. Free-form.
    :ivar forwarder_type: Destination type — see :class:`ForwarderType`.
    :ivar enabled: When ``False``, the audit service skips delivery for this
        forwarder but still records ``filtered_out`` deliveries.
    :ivar configuration: Destination request configuration.
    :ivar description: Optional free-text description.
    :ivar filter: Optional JSON Logic expression evaluated per event. When
        set, events that don't match are recorded as ``filtered_out``
        deliveries instead of being POSTed to the destination.
    :ivar transform: Optional template applied to each event before delivery.
        Shape depends on :attr:`transform_type`; for ``"JSONATA"``, a JSONata
        expression. ``None`` delivers the event JSON as-is.
    :ivar transform_type: Engine used to evaluate :attr:`transform`. Currently
        only ``"JSONATA"`` is supported.
    :ivar created_at: When the audit service first persisted this forwarder.
    :ivar updated_at: When this forwarder was last mutated.
    :ivar deleted_at: Soft-delete timestamp. ``None`` for live forwarders.
    :ivar version: Monotonic version counter; bumped on every server-side write.
    """

    id: UUID
    name: str
    forwarder_type: ForwarderType
    enabled: bool
    configuration: HttpConfiguration
    description: str | None = None
    filter: dict[str, Any] | None = None
    transform: str | None = None
    transform_type: str | None = None
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
            # Server-side validation already enforces enum membership;
            # we still pass through ForwarderType() so callers get a
            # typed value (and identity-equality with enum members).
            forwarder_type=ForwarderType(attrs["forwarder_type"]),
            enabled=bool(attrs.get("enabled", True)),
            description=attrs.get("description"),
            filter=attrs.get("filter"),
            transform=attrs.get("transform"),
            transform_type=attrs.get("transform_type"),
            configuration=HttpConfiguration._from_dict(attrs.get("configuration") or {}),
            created_at=_parse_iso_or_none(attrs.get("created_at")),
            updated_at=_parse_iso_or_none(attrs.get("updated_at")),
            deleted_at=_parse_iso_or_none(attrs.get("deleted_at")),
            version=attrs.get("version"),
        )


@dataclass(frozen=True, slots=True)
class ResourceType:
    """A distinct resource_type slug seen for the account.

    The ``id`` and ``resource_type`` fields are the same value — JSON:API
    surfaces the customer-facing key as the resource id (ADR-014 "key as
    id"). The duplication keeps SDK consumers from having to dig into
    the id field when filtering UI controls; pick whichever name reads
    better in context.

    :ivar id: The resource-type slug, surfaced as the JSON:API resource id.
    :ivar resource_type: Same value as :attr:`id`; provided for readability.
    :ivar created_at: Earliest sighting of this resource_type for the account.
    """

    id: str
    resource_type: str
    created_at: datetime

    @classmethod
    def _from_resource(cls, resource: dict[str, Any]) -> "ResourceType":
        attrs = resource.get("attributes", {})
        return cls(
            id=resource["id"],
            resource_type=attrs.get("resource_type") or resource["id"],
            created_at=_parse_iso(attrs["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class Action:
    """A distinct action slug seen for the account.

    Same shape as :class:`ResourceType` — ``id`` and ``action`` are the
    same value. When the parent list call filtered by ``resource_type``,
    ``created_at`` is the first sighting of that specific (action,
    resource_type) triple, not the action overall.

    :ivar id: The action slug, surfaced as the JSON:API resource id.
    :ivar action: Same value as :attr:`id`; provided for readability.
    :ivar created_at: Earliest sighting of this action (or action/resource_type
        pair when the list call was filtered) for the account.
    """

    id: str
    action: str
    created_at: datetime

    @classmethod
    def _from_resource(cls, resource: dict[str, Any]) -> "Action":
        attrs = resource.get("attributes", {})
        return cls(
            id=resource["id"],
            action=attrs.get("action") or resource["id"],
            created_at=_parse_iso(attrs["created_at"]),
        )


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
