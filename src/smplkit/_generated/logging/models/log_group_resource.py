from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import Literal

if TYPE_CHECKING:
    from ..models.log_group import LogGroup


T = TypeVar("T", bound="LogGroupResource")


@_attrs_define
class LogGroupResource:
    """
    Example:
        {'attributes': {'created_at': '2026-04-01T10:00:00Z', 'environments': {'production': {'level': 'ERROR'}},
            'level': 'WARN', 'name': 'Database Loggers', 'updated_at': '2026-04-01T10:00:00Z'}, 'id':
            '550e8400-e29b-41d4-a716-446655440000', 'type': 'log_group'}

    Attributes:
        type_ (Literal['log_group']):
        attributes (LogGroup):  Example: {'created_at': '2026-04-01T10:00:00Z', 'environments': {'production': {'level':
            'ERROR'}}, 'level': 'WARN', 'name': 'Database Loggers', 'updated_at': '2026-04-01T10:00:00Z'}.
        id (None | str | Unset):
    """

    type_: Literal["log_group"]
    attributes: LogGroup
    id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        attributes = self.attributes.to_dict()

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "attributes": attributes,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.log_group import LogGroup

        d = dict(src_dict)
        type_ = cast(Literal["log_group"], d.pop("type"))
        if type_ != "log_group":
            raise ValueError(f"type must match const 'log_group', got '{type_}'")

        attributes = LogGroup.from_dict(d.pop("attributes"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        log_group_resource = cls(
            type_=type_,
            attributes=attributes,
            id=id,
        )

        log_group_resource.additional_properties = d
        return log_group_resource

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
