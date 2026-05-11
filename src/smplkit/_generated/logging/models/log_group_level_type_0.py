from typing import Literal, cast

LogGroupLevelType0 = Literal["DEBUG", "ERROR", "FATAL", "INFO", "SILENT", "TRACE", "WARN"]

LOG_GROUP_LEVEL_TYPE_0_VALUES: set[LogGroupLevelType0] = {
    "DEBUG",
    "ERROR",
    "FATAL",
    "INFO",
    "SILENT",
    "TRACE",
    "WARN",
}


def check_log_group_level_type_0(value: str) -> LogGroupLevelType0:
    if value in LOG_GROUP_LEVEL_TYPE_0_VALUES:
        return cast(LogGroupLevelType0, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LOG_GROUP_LEVEL_TYPE_0_VALUES!r}")
