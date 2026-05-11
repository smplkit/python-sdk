from typing import Literal, cast

LoggerLevelType0 = Literal["DEBUG", "ERROR", "FATAL", "INFO", "SILENT", "TRACE", "WARN"]

LOGGER_LEVEL_TYPE_0_VALUES: set[LoggerLevelType0] = {
    "DEBUG",
    "ERROR",
    "FATAL",
    "INFO",
    "SILENT",
    "TRACE",
    "WARN",
}


def check_logger_level_type_0(value: str) -> LoggerLevelType0:
    if value in LOGGER_LEVEL_TYPE_0_VALUES:
        return cast(LoggerLevelType0, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LOGGER_LEVEL_TYPE_0_VALUES!r}")
