from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field


T = TypeVar("T", bound="CreateBundleAttributes")


@_attrs_define
class CreateBundleAttributes:
    """
    Example:
        {'bundle': 'standard', 'payment_method': 'pm_1234567890abcdef'}

    Attributes:
        bundle (str):
        payment_method (str):
    """

    bundle: str
    payment_method: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bundle = self.bundle

        payment_method = self.payment_method

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bundle": bundle,
                "payment_method": payment_method,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        bundle = d.pop("bundle")

        payment_method = d.pop("payment_method")

        create_bundle_attributes = cls(
            bundle=bundle,
            payment_method=payment_method,
        )

        create_bundle_attributes.additional_properties = d
        return create_bundle_attributes

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
