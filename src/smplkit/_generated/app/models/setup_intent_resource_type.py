from typing import Literal

SetupIntentResourceType = Literal["setup_intent"]

SETUP_INTENT_RESOURCE_TYPE_VALUES: set[SetupIntentResourceType] = {
    "setup_intent",
}


def check_setup_intent_resource_type(value: str) -> SetupIntentResourceType:
    if value in SETUP_INTENT_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SETUP_INTENT_RESOURCE_TYPE_VALUES!r}")
