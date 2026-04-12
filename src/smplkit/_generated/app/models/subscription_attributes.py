from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast


T = TypeVar("T", bound="SubscriptionAttributes")


@_attrs_define
class SubscriptionAttributes:
    """
    Attributes:
        product (str):
        plan (str):
        comped (bool):
        stripe_managed (bool):
        status (None | str | Unset):
        bundle (None | str | Unset):
        current_period_end (None | str | Unset):
        client_secret (None | str | Unset):
    """

    product: str
    plan: str
    comped: bool
    stripe_managed: bool
    status: None | str | Unset = UNSET
    bundle: None | str | Unset = UNSET
    current_period_end: None | str | Unset = UNSET
    client_secret: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        product = self.product

        plan = self.plan

        comped = self.comped

        stripe_managed = self.stripe_managed

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        bundle: None | str | Unset
        if isinstance(self.bundle, Unset):
            bundle = UNSET
        else:
            bundle = self.bundle

        current_period_end: None | str | Unset
        if isinstance(self.current_period_end, Unset):
            current_period_end = UNSET
        else:
            current_period_end = self.current_period_end

        client_secret: None | str | Unset
        if isinstance(self.client_secret, Unset):
            client_secret = UNSET
        else:
            client_secret = self.client_secret

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "product": product,
                "plan": plan,
                "comped": comped,
                "stripe_managed": stripe_managed,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if bundle is not UNSET:
            field_dict["bundle"] = bundle
        if current_period_end is not UNSET:
            field_dict["current_period_end"] = current_period_end
        if client_secret is not UNSET:
            field_dict["client_secret"] = client_secret

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        product = d.pop("product")

        plan = d.pop("plan")

        comped = d.pop("comped")

        stripe_managed = d.pop("stripe_managed")

        def _parse_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_bundle(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        bundle = _parse_bundle(d.pop("bundle", UNSET))

        def _parse_current_period_end(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        current_period_end = _parse_current_period_end(d.pop("current_period_end", UNSET))

        def _parse_client_secret(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        client_secret = _parse_client_secret(d.pop("client_secret", UNSET))

        subscription_attributes = cls(
            product=product,
            plan=plan,
            comped=comped,
            stripe_managed=stripe_managed,
            status=status,
            bundle=bundle,
            current_period_end=current_period_end,
            client_secret=client_secret,
        )

        subscription_attributes.additional_properties = d
        return subscription_attributes

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
