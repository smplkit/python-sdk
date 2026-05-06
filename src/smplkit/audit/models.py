"""Audit event resource model exposed by the SDK."""

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
        )


def _parse_iso(value: str) -> datetime:
    # Python's fromisoformat accepts an optional trailing 'Z' (treated as UTC)
    # in 3.11+. The audit service emits +00:00 anyway, but customers may pass
    # ``Z`` from JS-flavored timestamps.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)
