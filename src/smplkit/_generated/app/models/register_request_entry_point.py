from typing import Literal, cast

RegisterRequestEntryPoint = Literal["get_started", "live_demo", "login", "unknown"]

REGISTER_REQUEST_ENTRY_POINT_VALUES: set[RegisterRequestEntryPoint] = {
    "get_started",
    "live_demo",
    "login",
    "unknown",
}


def check_register_request_entry_point(value: str) -> RegisterRequestEntryPoint:
    if value in REGISTER_REQUEST_ENTRY_POINT_VALUES:
        return cast(RegisterRequestEntryPoint, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {REGISTER_REQUEST_ENTRY_POINT_VALUES!r}")
