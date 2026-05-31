from typing import Literal

SubscriptionResponseAttributesDiscountSource = Literal["OVERRIDE", "VOLUME"]

SUBSCRIPTION_RESPONSE_ATTRIBUTES_DISCOUNT_SOURCE_VALUES: set[SubscriptionResponseAttributesDiscountSource] = {
    "OVERRIDE",
    "VOLUME",
}


def check_subscription_response_attributes_discount_source(value: str) -> SubscriptionResponseAttributesDiscountSource:
    if value in SUBSCRIPTION_RESPONSE_ATTRIBUTES_DISCOUNT_SOURCE_VALUES:
        return value
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {SUBSCRIPTION_RESPONSE_ATTRIBUTES_DISCOUNT_SOURCE_VALUES!r}"
    )
