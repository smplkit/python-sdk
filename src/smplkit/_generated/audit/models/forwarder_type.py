from typing import Literal, cast

ForwarderType = Literal["DATADOG", "ELASTIC", "HONEYCOMB", "HTTP", "NEW_RELIC", "SPLUNK_HEC", "SUMO_LOGIC"]

FORWARDER_TYPE_VALUES: set[ForwarderType] = {
    "DATADOG",
    "ELASTIC",
    "HONEYCOMB",
    "HTTP",
    "NEW_RELIC",
    "SPLUNK_HEC",
    "SUMO_LOGIC",
}


def check_forwarder_type(value: str) -> ForwarderType:
    if value in FORWARDER_TYPE_VALUES:
        return cast(ForwarderType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {FORWARDER_TYPE_VALUES!r}")
