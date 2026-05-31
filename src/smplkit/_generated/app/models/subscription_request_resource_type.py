from typing import Literal

SubscriptionRequestResourceType = Literal["subscription"]

SUBSCRIPTION_REQUEST_RESOURCE_TYPE_VALUES: set[SubscriptionRequestResourceType] = {
    "subscription",
}


def check_subscription_request_resource_type(value: str) -> SubscriptionRequestResourceType:
    if value in SUBSCRIPTION_REQUEST_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SUBSCRIPTION_REQUEST_RESOURCE_TYPE_VALUES!r}")
