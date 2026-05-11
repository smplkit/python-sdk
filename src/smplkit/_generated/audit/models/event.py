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


T = TypeVar("T", bound="Event")


@_attrs_define
class Event:
    """An audit event — a record that something happened, attributed to
    an actor and a resource.

    When recording a snapshot of the resource at the time of the event,
    place it inside `data`. smplkit's own integrations nest it under
    `data.snapshot`, but the slot is yours to use however you like.

        Attributes:
            action (str): Slug for what happened, e.g. `user.created`. Lowercase, dot-separated.
            resource_type (str): Slug for the kind of resource the event is about, e.g. `user`. Lowercase, dot-separated.
            resource_id (str): Identifier of the specific resource the event is about.
            occurred_at (datetime.datetime | None | Unset): When the event actually happened. Defaults to the server receipt
                time (`created_at`).
            data (EventData | Unset): Free-form payload attached to the event. Use it for resource snapshots (by convention
                under `data.snapshot`), request identifiers, or any other context the event needs to carry.
            do_not_forward (bool | Unset): When `true`, the event is recorded but not delivered to any forwarder. A delivery
                log entry with status `SKIPPED_DO_NOT_FORWARD` is written for each enabled forwarder so the skip is visible in
                the delivery log. Default: False.
            created_at (datetime.datetime | None | Unset): When the event was received and recorded.
            actor_type (None | str | Unset): Kind of credential that emitted the event, e.g. `USER` or `API_KEY`. Resolved
                server-side from the request credential.
            actor_id (None | Unset | UUID): Identifier of the actor that emitted the event.
            actor_label (None | str | Unset): Human-readable label for the actor (e.g. the user's email address or the API
                key name) at the time the event was recorded.
            idempotency_key (None | str | Unset): The idempotency key used to deduplicate the record. Echoes the
                `Idempotency-Key` header if one was supplied, otherwise a key derived from the event's content.
    """

    action: str
    resource_type: str
    resource_id: str
    occurred_at: datetime.datetime | None | Unset = UNSET
    data: EventData | Unset = UNSET
    do_not_forward: bool | Unset = False
    created_at: datetime.datetime | None | Unset = UNSET
    actor_type: None | str | Unset = UNSET
    actor_id: None | Unset | UUID = UNSET
    actor_label: None | str | Unset = UNSET
    idempotency_key: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
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

        data: dict[str, Any] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        do_not_forward = self.do_not_forward

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
        if data is not UNSET:
            field_dict["data"] = data
        if do_not_forward is not UNSET:
            field_dict["do_not_forward"] = do_not_forward
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

        _data = d.pop("data", UNSET)
        data: EventData | Unset
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = EventData.from_dict(_data)

        do_not_forward = d.pop("do_not_forward", UNSET)

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
            data=data,
            do_not_forward=do_not_forward,
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
