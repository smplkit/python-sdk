from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field


if TYPE_CHECKING:
    from ..models.config_resource import ConfigResource


T = TypeVar("T", bound="ConfigListResponse")


@_attrs_define
class ConfigListResponse:
    """
    Example:
        {'data': [{'attributes': {'created_at': '2026-03-27T10:00:00Z', 'description': 'PostgreSQL connection string',
            'environments': {'production': {}, 'staging': {}}, 'key': 'database_url', 'name': 'Database URL', 'updated_at':
            '2026-03-27T10:00:00Z', 'values': {'production': 'postgresql://prod-db:5432/smplkit'}}, 'id':
            '550e8400-e29b-41d4-a716-446655440000', 'type': 'config'}, {'attributes': {'created_at': '2026-03-27T10:00:00Z',
            'description': 'Application log level', 'environments': {'production': {}, 'staging': {}}, 'key': 'log_level',
            'name': 'Log Level', 'updated_at': '2026-03-27T10:00:00Z', 'values': {'production': 'info', 'staging':
            'debug'}}, 'id': '660e8400-e29b-41d4-a716-446655440001', 'type': 'config'}]}

    Attributes:
        data (list[ConfigResource]):
    """

    data: list[ConfigResource]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = []
        for data_item_data in self.data:
            data_item = data_item_data.to_dict()
            data.append(data_item)

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
        from ..models.config_resource import ConfigResource

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = ConfigResource.from_dict(data_item_data)

            data.append(data_item)

        config_list_response = cls(
            data=data,
        )

        config_list_response.additional_properties = d
        return config_list_response

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
