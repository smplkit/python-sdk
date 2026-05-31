from typing import Literal

ContactTopic = Literal["account", "billing", "feature_request", "other", "technical"]

CONTACT_TOPIC_VALUES: set[ContactTopic] = {
    "account",
    "billing",
    "feature_request",
    "other",
    "technical",
}


def check_contact_topic(value: str) -> ContactTopic:
    if value in CONTACT_TOPIC_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CONTACT_TOPIC_VALUES!r}")
