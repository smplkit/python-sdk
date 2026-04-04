from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field


if TYPE_CHECKING:
    from ..models.log_group_resource import LogGroupResource


T = TypeVar("T", bound="LogGroupResponse")


@_attrs_define
class LogGroupResponse:
    """
    Attributes:
        data (LogGroupResource):  Example: {'attributes': {'created_at': '2026-04-01T10:00:00Z', 'environments':
            {'production': {'level': 'ERROR'}}, 'key': 'database-loggers', 'level': 'WARN', 'name': 'Database Loggers',
            'updated_at': '2026-04-01T10:00:00Z'}, 'id': '550e8400-e29b-41d4-a716-446655440000', 'type': 'log_group'}.
    """

    data: LogGroupResource
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.log_group_resource import LogGroupResource

        d = dict(src_dict)
        data = LogGroupResource.from_dict(d.pop("data"))

        log_group_response = cls(
            data=data,
        )

        log_group_response.additional_properties = d
        return log_group_response

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
