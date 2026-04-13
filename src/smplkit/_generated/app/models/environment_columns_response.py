from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field


if TYPE_CHECKING:
    from ..models.environment_column_item import EnvironmentColumnItem


T = TypeVar("T", bound="EnvironmentColumnsResponse")


@_attrs_define
class EnvironmentColumnsResponse:
    """
    Attributes:
        environment_columns (list[EnvironmentColumnItem]):
    """

    environment_columns: list[EnvironmentColumnItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        environment_columns = []
        for environment_columns_item_data in self.environment_columns:
            environment_columns_item = environment_columns_item_data.to_dict()
            environment_columns.append(environment_columns_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "environment_columns": environment_columns,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.environment_column_item import EnvironmentColumnItem

        d = dict(src_dict)
        environment_columns = []
        _environment_columns = d.pop("environment_columns")
        for environment_columns_item_data in _environment_columns:
            environment_columns_item = EnvironmentColumnItem.from_dict(environment_columns_item_data)

            environment_columns.append(environment_columns_item)

        environment_columns_response = cls(
            environment_columns=environment_columns,
        )

        environment_columns_response.additional_properties = d
        return environment_columns_response

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
