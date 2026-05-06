from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from dateutil.parser import isoparse
from typing import cast
from uuid import UUID
import datetime

if TYPE_CHECKING:
    from ..models.event_data import EventData
    from ..models.event_snapshot_type_0 import EventSnapshotType0


T = TypeVar("T", bound="Event")


@_attrs_define
class Event:
    """Public-facing event resource.

    Attribute set on POST /api/v1/events:
        - action (required)
        - resource_type (required)
        - resource_id (required)
        - occurred_at (optional; defaults to ``created_at``)
        - snapshot (optional)
        - data (optional; defaults to ``{}``)

    Attribute set on GET responses includes everything above plus the
    server-populated fields: ``created_at``, ``actor_type``, ``actor_id``,
    ``actor_label``, ``idempotency_key``.

        Attributes:
            action (str):
            resource_type (str):
            resource_id (str):
            occurred_at (datetime.datetime | None | Unset):
            snapshot (EventSnapshotType0 | None | Unset):
            data (EventData | Unset):
            created_at (datetime.datetime | None | Unset):
            actor_type (None | str | Unset):
            actor_id (None | Unset | UUID):
            actor_label (None | str | Unset):
            idempotency_key (None | str | Unset):
    """

    action: str
    resource_type: str
    resource_id: str
    occurred_at: datetime.datetime | None | Unset = UNSET
    snapshot: EventSnapshotType0 | None | Unset = UNSET
    data: EventData | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    actor_type: None | str | Unset = UNSET
    actor_id: None | Unset | UUID = UNSET
    actor_label: None | str | Unset = UNSET
    idempotency_key: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.event_snapshot_type_0 import EventSnapshotType0

        action = self.action

        resource_type = self.resource_type

        resource_id = self.resource_id

        occurred_at: None | str | Unset
        if isinstance(self.occurred_at, Unset):
            occurred_at = UNSET
        elif isinstance(self.occurred_at, datetime.datetime):
            occurred_at = self.occurred_at.isoformat()
        else:
            occurred_at = self.occurred_at

        snapshot: dict[str, Any] | None | Unset
        if isinstance(self.snapshot, Unset):
            snapshot = UNSET
        elif isinstance(self.snapshot, EventSnapshotType0):
            snapshot = self.snapshot.to_dict()
        else:
            snapshot = self.snapshot

        data: dict[str, Any] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        actor_type: None | str | Unset
        if isinstance(self.actor_type, Unset):
            actor_type = UNSET
        else:
            actor_type = self.actor_type

        actor_id: None | str | Unset
        if isinstance(self.actor_id, Unset):
            actor_id = UNSET
        elif isinstance(self.actor_id, UUID):
            actor_id = str(self.actor_id)
        else:
            actor_id = self.actor_id

        actor_label: None | str | Unset
        if isinstance(self.actor_label, Unset):
            actor_label = UNSET
        else:
            actor_label = self.actor_label

        idempotency_key: None | str | Unset
        if isinstance(self.idempotency_key, Unset):
            idempotency_key = UNSET
        else:
            idempotency_key = self.idempotency_key

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
            }
        )
        if occurred_at is not UNSET:
            field_dict["occurred_at"] = occurred_at
        if snapshot is not UNSET:
            field_dict["snapshot"] = snapshot
        if data is not UNSET:
            field_dict["data"] = data
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if actor_type is not UNSET:
            field_dict["actor_type"] = actor_type
        if actor_id is not UNSET:
            field_dict["actor_id"] = actor_id
        if actor_label is not UNSET:
            field_dict["actor_label"] = actor_label
        if idempotency_key is not UNSET:
            field_dict["idempotency_key"] = idempotency_key

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.event_data import EventData
        from ..models.event_snapshot_type_0 import EventSnapshotType0

        d = dict(src_dict)
        action = d.pop("action")

        resource_type = d.pop("resource_type")

        resource_id = d.pop("resource_id")

        def _parse_occurred_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                occurred_at_type_0 = isoparse(data)

                return occurred_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        occurred_at = _parse_occurred_at(d.pop("occurred_at", UNSET))

        def _parse_snapshot(data: object) -> EventSnapshotType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                snapshot_type_0 = EventSnapshotType0.from_dict(data)

                return snapshot_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(EventSnapshotType0 | None | Unset, data)

        snapshot = _parse_snapshot(d.pop("snapshot", UNSET))

        _data = d.pop("data", UNSET)
        data: EventData | Unset
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = EventData.from_dict(_data)

        def _parse_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = isoparse(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_actor_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_type = _parse_actor_type(d.pop("actor_type", UNSET))

        def _parse_actor_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                actor_id_type_0 = UUID(data)

                return actor_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        actor_id = _parse_actor_id(d.pop("actor_id", UNSET))

        def _parse_actor_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_label = _parse_actor_label(d.pop("actor_label", UNSET))

        def _parse_idempotency_key(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        idempotency_key = _parse_idempotency_key(d.pop("idempotency_key", UNSET))

        event = cls(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            occurred_at=occurred_at,
            snapshot=snapshot,
            data=data,
            created_at=created_at,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_label=actor_label,
            idempotency_key=idempotency_key,
        )

        event.additional_properties = d
        return event

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
