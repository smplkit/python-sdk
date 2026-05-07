from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.subscription_list_meta_discount_source import check_subscription_list_meta_discount_source
from ..models.subscription_list_meta_discount_source import SubscriptionListMetaDiscountSource

if TYPE_CHECKING:
    from ..models.next_tier_meta import NextTierMeta


T = TypeVar("T", bound="SubscriptionListMeta")


@_attrs_define
class SubscriptionListMeta:
    """Discount and totals summary attached to GET /api/v1/subscriptions.

    Attributes:
        subtotal_cents (int):
        discount_pct (int):
        discount_amount_cents (int):
        discount_source (SubscriptionListMetaDiscountSource):
        total_cents (int):
        next_tier (NextTierMeta | Unset):
    """

    subtotal_cents: int
    discount_pct: int
    discount_amount_cents: int
    discount_source: SubscriptionListMetaDiscountSource
    total_cents: int
    next_tier: NextTierMeta | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subtotal_cents = self.subtotal_cents

        discount_pct = self.discount_pct

        discount_amount_cents = self.discount_amount_cents

        discount_source: str = self.discount_source

        total_cents = self.total_cents

        next_tier: dict[str, Any] | Unset = UNSET
        if not isinstance(self.next_tier, Unset):
            next_tier = self.next_tier.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subtotal_cents": subtotal_cents,
                "discount_pct": discount_pct,
                "discount_amount_cents": discount_amount_cents,
                "discount_source": discount_source,
                "total_cents": total_cents,
            }
        )
        if next_tier is not UNSET:
            field_dict["next_tier"] = next_tier

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.next_tier_meta import NextTierMeta

        d = dict(src_dict)
        subtotal_cents = d.pop("subtotal_cents")

        discount_pct = d.pop("discount_pct")

        discount_amount_cents = d.pop("discount_amount_cents")

        discount_source = check_subscription_list_meta_discount_source(d.pop("discount_source"))

        total_cents = d.pop("total_cents")

        _next_tier = d.pop("next_tier", UNSET)
        next_tier: NextTierMeta | Unset
        if isinstance(_next_tier, Unset):
            next_tier = UNSET
        else:
            next_tier = NextTierMeta.from_dict(_next_tier)

        subscription_list_meta = cls(
            subtotal_cents=subtotal_cents,
            discount_pct=discount_pct,
            discount_amount_cents=discount_amount_cents,
            discount_source=discount_source,
            total_cents=total_cents,
            next_tier=next_tier,
        )

        subscription_list_meta.additional_properties = d
        return subscription_list_meta

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
