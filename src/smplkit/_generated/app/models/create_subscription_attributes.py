from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast


T = TypeVar("T", bound="CreateSubscriptionAttributes")


@_attrs_define
class CreateSubscriptionAttributes:
    """
    Example:
        {'payment_method': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'plan': 'pro', 'product': 'flags'}

    Attributes:
        product (str):
        plan (str):
        payment_method (None | str | Unset):
    """

    product: str
    plan: str
    payment_method: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        product = self.product

        plan = self.plan

        payment_method: None | str | Unset
        if isinstance(self.payment_method, Unset):
            payment_method = UNSET
        else:
            payment_method = self.payment_method

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "product": product,
                "plan": plan,
            }
        )
        if payment_method is not UNSET:
            field_dict["payment_method"] = payment_method

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        product = d.pop("product")

        plan = d.pop("plan")

        def _parse_payment_method(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        payment_method = _parse_payment_method(d.pop("payment_method", UNSET))

        create_subscription_attributes = cls(
            product=product,
            plan=plan,
            payment_method=payment_method,
        )

        create_subscription_attributes.additional_properties = d
        return create_subscription_attributes

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
