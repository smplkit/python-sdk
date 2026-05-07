from typing import Literal, cast

ForwarderDeliveryStatus = Literal["failed", "filtered_out", "skipped_do_not_forward", "succeeded"]

FORWARDER_DELIVERY_STATUS_VALUES: set[ForwarderDeliveryStatus] = {
    "failed",
    "filtered_out",
    "skipped_do_not_forward",
    "succeeded",
}


def check_forwarder_delivery_status(value: str) -> ForwarderDeliveryStatus:
    if value in FORWARDER_DELIVERY_STATUS_VALUES:
        return cast(ForwarderDeliveryStatus, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {FORWARDER_DELIVERY_STATUS_VALUES!r}")
