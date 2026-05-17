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
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from smplkit.management.audit import ForwardersClient


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

    :ivar UUID id: Server-assigned UUID for this event.
    :ivar str action: Action slug — e.g. ``"user.created"``, ``"invoice.paid"``.
    :ivar str resource_type: Type of resource the action operated on — e.g. ``"invoice"``.
    :ivar str resource_id: Customer-facing id of the resource the action operated on.
    :ivar str actor_type: Type of the actor that performed the action (``"user"``,
        ``"api_key"``, ``"system"``, …). Empty string when unknown.
    :ivar str actor_label: Display label for the actor — typically a name or email.
        Empty string when unknown.
    :ivar datetime occurred_at: When the action actually happened, as reported by
        the source.
    :ivar datetime created_at: When the audit service first ingested this event.
    :ivar UUID | None actor_id: UUID of the actor, when the actor is a tracked
        entity (user, api_key). ``None`` for system actors or anonymous events.
    :ivar dict[str, Any] data: Free-form per-event payload defined by the customer.
        Surfaced on the audit-event resource as a structured JSONB column.
    :ivar str idempotency_key: Customer-supplied dedupe key. Empty when the
        customer didn't supply one.
    :ivar bool do_not_forward: When ``True``, skip this event from SIEM forwarder
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

    :ivar str name: Header name (e.g. ``"Authorization"``, ``"DD-API-KEY"``).
    :ivar str value: Header value, plaintext on writes. The audit service encrypts
        values at rest; reads return them as ``"<redacted>"``.
    """

    name: str
    value: str

    def _to_dict(self) -> dict[str, str]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True, slots=True)
class HttpConfiguration:
    """Forwarder destination HTTP request shape.

    :ivar HttpMethod method: HTTP verb used for delivery. Defaults to ``HttpMethod.POST``.
    :ivar str url: Destination URL the audit service POSTs each event to.
    :ivar list[HttpHeader] headers: Headers attached to every outbound request.
        Values carry credentials and are encrypted at rest server-side; reads
        return them redacted.
    :ivar str success_status: Status the destination must return for delivery to
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


class Forwarder:
    """A SIEM streaming forwarder configured on the customer's account.

    Active-record style: mutate fields directly and call :meth:`save` to
    persist, or :meth:`delete` to remove. Header values in
    ``configuration.headers`` are always returned redacted on reads — the
    GET path on the audit API replaces every header value with
    ``"<redacted>"``. Re-supply the real values before calling
    :meth:`save` (the SDK does not cache them client-side).

    :ivar UUID | None id: Server-assigned UUID for this forwarder. ``None`` until
        :meth:`save` has run for the first time.
    :ivar str name: Display name. Free-form.
    :ivar ForwarderType forwarder_type: Destination type — see :class:`ForwarderType`.
    :ivar bool enabled: When ``False``, the audit service skips delivery for this
        forwarder but still records ``filtered_out`` deliveries.
    :ivar HttpConfiguration configuration: Destination request configuration.
    :ivar str | None description: Optional free-text description.
    :ivar dict[str, Any] | None filter: Optional JSON Logic expression evaluated
        per event. When set, events that don't match are recorded as
        ``filtered_out`` deliveries instead of being POSTed to the destination.
    :ivar str | None transform: Optional template applied to each event before
        delivery. Shape depends on :attr:`transform_type`; for ``"JSONATA"``, a
        JSONata expression. ``None`` delivers the event JSON as-is.
    :ivar str | None transform_type: Engine used to evaluate :attr:`transform`.
        Currently only ``"JSONATA"`` is supported.
    :ivar datetime | None created_at: When the audit service first persisted this
        forwarder. ``None`` for an unsaved instance.
    :ivar datetime | None updated_at: When this forwarder was last mutated.
    :ivar datetime | None deleted_at: Soft-delete timestamp. ``None`` for live
        forwarders.
    :ivar int | None version: Monotonic version counter; bumped on every
        server-side write.
    """

    def __init__(
        self,
        client: ForwardersClient | None = None,
        *,
        id: UUID | None = None,
        name: str,
        forwarder_type: ForwarderType,
        configuration: HttpConfiguration,
        enabled: bool = True,
        description: str | None = None,
        filter: dict[str, Any] | None = None,
        transform: str | None = None,
        transform_type: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.forwarder_type = forwarder_type
        self.configuration = configuration
        self.enabled = enabled
        self.description = description
        self.filter = filter
        self.transform = transform
        self.transform_type = transform_type
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.version = version
        self._client = client

    def __repr__(self) -> str:
        return f"Forwarder(id={self.id!r}, name={self.name!r}, enabled={self.enabled!r})"

    def save(self) -> None:
        """Create or update this forwarder on the server.

        Upsert behavior is driven by :attr:`created_at`: a forwarder with
        no ``created_at`` is created (POST); otherwise it's full-replace
        updated (PUT). After the call, every field is refreshed from the
        server response (including newly-assigned ``id``, ``created_at``,
        ``updated_at``, ``version``).
        """
        if self._client is None:
            raise RuntimeError("Forwarder was constructed without a client; cannot save")
        if self.created_at is None:
            other = self._client._create(self)
        else:
            other = self._client._update(self)
        self._apply(other)

    def delete(self) -> None:
        """Soft-delete this forwarder on the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("Forwarder was constructed without a client or id; cannot delete")
        self._client.delete(self.id)

    def _apply(self, other: Forwarder) -> None:
        """Copy every server-authoritative field from ``other`` onto self."""
        self.id = other.id
        self.name = other.name
        self.forwarder_type = other.forwarder_type
        self.configuration = other.configuration
        self.enabled = other.enabled
        self.description = other.description
        self.filter = other.filter
        self.transform = other.transform
        self.transform_type = other.transform_type
        self.created_at = other.created_at
        self.updated_at = other.updated_at
        self.deleted_at = other.deleted_at
        self.version = other.version

    @classmethod
    def _from_resource(cls, resource: dict[str, Any], *, client: ForwardersClient | None = None) -> Forwarder:
        attrs = resource.get("attributes", {})
        return cls(
            client,
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

    :ivar str id: The resource-type slug, surfaced as the JSON:API resource id.
    :ivar str resource_type: Same value as :attr:`id`; provided for readability.
    :ivar datetime created_at: Earliest sighting of this resource_type for the
        account.
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

    :ivar str id: The action slug, surfaced as the JSON:API resource id.
    :ivar str action: Same value as :attr:`id`; provided for readability.
    :ivar datetime created_at: Earliest sighting of this action (or
        action/resource_type pair when the list call was filtered) for the
        account.
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
