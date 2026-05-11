from typing import Literal, cast

ForwarderHttpMethod = Literal["DELETE", "GET", "PATCH", "POST", "PUT"]

FORWARDER_HTTP_METHOD_VALUES: set[ForwarderHttpMethod] = {
    "DELETE",
    "GET",
    "PATCH",
    "POST",
    "PUT",
}


def check_forwarder_http_method(value: str) -> ForwarderHttpMethod:
    if value in FORWARDER_HTTP_METHOD_VALUES:
        return cast(ForwarderHttpMethod, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {FORWARDER_HTTP_METHOD_VALUES!r}")
