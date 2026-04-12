from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field


from typing import cast


T = TypeVar("T", bound="CatalogBundleAttributes")


@_attrs_define
class CatalogBundleAttributes:
    """
    Attributes:
        display_name (str):
        plan (str):
        products (list[str]):
        price_monthly_cents (int):
    """

    display_name: str
    plan: str
    products: list[str]
    price_monthly_cents: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        display_name = self.display_name

        plan = self.plan

        products = self.products

        price_monthly_cents = self.price_monthly_cents

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "display_name": display_name,
                "plan": plan,
                "products": products,
                "price_monthly_cents": price_monthly_cents,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        display_name = d.pop("display_name")

        plan = d.pop("plan")

        products = cast(list[str], d.pop("products"))

        price_monthly_cents = d.pop("price_monthly_cents")

        catalog_bundle_attributes = cls(
            display_name=display_name,
            plan=plan,
            products=products,
            price_monthly_cents=price_monthly_cents,
        )

        catalog_bundle_attributes.additional_properties = d
        return catalog_bundle_attributes

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
