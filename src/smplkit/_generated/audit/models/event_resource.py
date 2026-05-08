from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


if TYPE_CHECKING:
    from ..models.event import Event


T = TypeVar("T", bound="EventResource")


@_attrs_define
class EventResource:
    """JSON:API resource envelope for an audit event.

    Example:
        {'attributes': {'action': 'user.created', 'actor_id': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'actor_label':
            'alice@example.com', 'actor_type': 'USER', 'created_at': '2026-05-06T20:00:00.123Z', 'data': {'request_id':
            'req-abc', 'snapshot': {'email': 'alice@example.com'}}, 'do_not_forward': False, 'idempotency_key':
            'auto-1234abcd', 'occurred_at': '2026-05-06T20:00:00Z', 'resource_id': 'u-1', 'resource_type': 'user'}, 'id':
            '11111111-2222-3333-4444-555555555555', 'type': 'event'}

    Attributes:
        id (str):
        attributes (Event): Public-facing event resource.

            Attribute set on POST /api/v1/events:
                - action (required)
                - resource_type (required)
                - resource_id (required)
                - occurred_at (optional; defaults to ``created_at``)
                - data (optional; defaults to ``{}``)

            There is no top-level ``snapshot`` attribute. Customers wishing to
            record a resource snapshot place it inside ``data`` -- smplkit's
            internal convention nests it at ``data.snapshot``, but customers may
            follow their own convention.

            Attribute set on GET responses includes everything above plus the
            server-populated fields: ``created_at``, ``actor_type``, ``actor_id``,
            ``actor_label``, ``idempotency_key``.
        type_ (str | Unset):  Default: 'event'.
    """

    id: str
    attributes: Event
    type_: str | Unset = "event"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        attributes = self.attributes.to_dict()

        type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "attributes": attributes,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.event import Event

        d = dict(src_dict)
        id = d.pop("id")

        attributes = Event.from_dict(d.pop("attributes"))

        type_ = d.pop("type", UNSET)

        event_resource = cls(
            id=id,
            attributes=attributes,
            type_=type_,
        )

        event_resource.additional_properties = d
        return event_resource

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
