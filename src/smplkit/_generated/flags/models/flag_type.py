from typing import Literal

FlagType = Literal["BOOLEAN", "JSON", "NUMERIC", "STRING"]

FLAG_TYPE_VALUES: set[FlagType] = {
    "BOOLEAN",
    "JSON",
    "NUMERIC",
    "STRING",
}


def check_flag_type(value: str) -> FlagType:
    if value in FLAG_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {FLAG_TYPE_VALUES!r}")
