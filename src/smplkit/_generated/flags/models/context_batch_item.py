from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


if TYPE_CHECKING:
    from ..models.context_batch_item_attributes import ContextBatchItemAttributes


T = TypeVar("T", bound="ContextBatchItem")


@_attrs_define
class ContextBatchItem:
    """
    Attributes:
        type_ (str): Context type key (e.g., 'user', 'account')
        key (str): Entity identifier (e.g., 'user-123')
        attributes (ContextBatchItemAttributes | Unset):
    """

    type_: str
    key: str
    attributes: ContextBatchItemAttributes | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        key = self.key

        attributes: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attributes, Unset):
            attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "key": key,
            }
        )
        if attributes is not UNSET:
            field_dict["attributes"] = attributes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.context_batch_item_attributes import ContextBatchItemAttributes

        d = dict(src_dict)
        type_ = d.pop("type")

        key = d.pop("key")

        _attributes = d.pop("attributes", UNSET)
        attributes: ContextBatchItemAttributes | Unset
        if isinstance(_attributes, Unset):
            attributes = UNSET
        else:
            attributes = ContextBatchItemAttributes.from_dict(_attributes)

        context_batch_item = cls(
            type_=type_,
            key=key,
            attributes=attributes,
        )

        context_batch_item.additional_properties = d
        return context_batch_item

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
