from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field


from ..models.create_bundle_data_type import check_create_bundle_data_type
from ..models.create_bundle_data_type import CreateBundleDataType

if TYPE_CHECKING:
    from ..models.create_bundle_attributes import CreateBundleAttributes


T = TypeVar("T", bound="CreateBundleData")


@_attrs_define
class CreateBundleData:
    """
    Attributes:
        type_ (CreateBundleDataType):
        attributes (CreateBundleAttributes):  Example: {'bundle': 'standard', 'payment_method':
            'a1b2c3d4-e5f6-7890-abcd-ef1234567890'}.
    """

    type_: CreateBundleDataType
    attributes: CreateBundleAttributes
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_: str = self.type_

        attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "attributes": attributes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_bundle_attributes import CreateBundleAttributes

        d = dict(src_dict)
        type_ = check_create_bundle_data_type(d.pop("type"))

        attributes = CreateBundleAttributes.from_dict(d.pop("attributes"))

        create_bundle_data = cls(
            type_=type_,
            attributes=attributes,
        )

        create_bundle_data.additional_properties = d
        return create_bundle_data

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
