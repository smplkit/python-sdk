from typing import Literal, cast

SubscriptionListMetaDiscountSource = Literal["override", "volume"]

SUBSCRIPTION_LIST_META_DISCOUNT_SOURCE_VALUES: set[SubscriptionListMetaDiscountSource] = {
    "override",
    "volume",
}


def check_subscription_list_meta_discount_source(value: str) -> SubscriptionListMetaDiscountSource:
    if value in SUBSCRIPTION_LIST_META_DISCOUNT_SOURCE_VALUES:
        return cast(SubscriptionListMetaDiscountSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SUBSCRIPTION_LIST_META_DISCOUNT_SOURCE_VALUES!r}")
