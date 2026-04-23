from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


T = TypeVar("T", bound="AddPaymentMethodAttributes")


@_attrs_define
class AddPaymentMethodAttributes:
    """Attributes for POST /api/v1/payment_methods.

    Distinct from ``PaymentMethod`` because this shape takes the Stripe
    ``pm_...`` ID at registration time; the persistent resource does not
    expose that ID.

        Example:
            {'default': False, 'stripe_payment_method_id': 'pm_1234567890abcdef'}

        Attributes:
            stripe_payment_method_id (str):
            default (bool | Unset):  Default: False.
    """

    stripe_payment_method_id: str
    default: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        stripe_payment_method_id = self.stripe_payment_method_id

        default = self.default

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "stripe_payment_method_id": stripe_payment_method_id,
            }
        )
        if default is not UNSET:
            field_dict["default"] = default

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        stripe_payment_method_id = d.pop("stripe_payment_method_id")

        default = d.pop("default", UNSET)

        add_payment_method_attributes = cls(
            stripe_payment_method_id=stripe_payment_method_id,
            default=default,
        )

        add_payment_method_attributes.additional_properties = d
        return add_payment_method_attributes

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
