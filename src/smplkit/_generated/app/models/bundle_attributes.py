from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field


from typing import cast


T = TypeVar("T", bound="BundleAttributes")


@_attrs_define
class BundleAttributes:
    """
    Attributes:
        bundle (str):
        plan (str):
        products (list[str]):
        subscriptions (list[str]):
    """

    bundle: str
    plan: str
    products: list[str]
    subscriptions: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bundle = self.bundle

        plan = self.plan

        products = self.products

        subscriptions = self.subscriptions

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bundle": bundle,
                "plan": plan,
                "products": products,
                "subscriptions": subscriptions,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        bundle = d.pop("bundle")

        plan = d.pop("plan")

        products = cast(list[str], d.pop("products"))

        subscriptions = cast(list[str], d.pop("subscriptions"))

        bundle_attributes = cls(
            bundle=bundle,
            plan=plan,
            products=products,
            subscriptions=subscriptions,
        )

        bundle_attributes.additional_properties = d
        return bundle_attributes

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
