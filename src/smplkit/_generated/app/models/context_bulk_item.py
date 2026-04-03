from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.context_bulk_item_attributes import ContextBulkItemAttributes


T = TypeVar("T", bound="ContextBulkItem")


@_attrs_define
class ContextBulkItem:
    """
    Attributes:
        id (str): Composite logical ID: type:key (e.g., 'user:123')
        name (None | str | Unset): Human-readable display name; defaults to key
        attributes (ContextBulkItemAttributes | Unset):
    """

    id: str
    name: None | str | Unset = UNSET
    attributes: ContextBulkItemAttributes | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        attributes: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attributes, Unset):
            attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name
        if attributes is not UNSET:
            field_dict["attributes"] = attributes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.context_bulk_item_attributes import ContextBulkItemAttributes

        d = dict(src_dict)
        id = d.pop("id")

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        _attributes = d.pop("attributes", UNSET)
        attributes: ContextBulkItemAttributes | Unset
        if isinstance(_attributes, Unset):
            attributes = UNSET
        else:
            attributes = ContextBulkItemAttributes.from_dict(_attributes)

        context_bulk_item = cls(
            id=id,
            name=name,
            attributes=attributes,
        )

        context_bulk_item.additional_properties = d
        return context_bulk_item

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
