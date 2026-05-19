from typing import Literal, cast

LoggerEffectiveLevelsType0AdditionalPropertyItem = Literal["DEBUG", "ERROR", "FATAL", "INFO", "SILENT", "TRACE", "WARN"]

LOGGER_EFFECTIVE_LEVELS_TYPE_0_ADDITIONAL_PROPERTY_ITEM_VALUES: set[
    LoggerEffectiveLevelsType0AdditionalPropertyItem
] = {
    "DEBUG",
    "ERROR",
    "FATAL",
    "INFO",
    "SILENT",
    "TRACE",
    "WARN",
}


def check_logger_effective_levels_type_0_additional_property_item(
    value: str,
) -> LoggerEffectiveLevelsType0AdditionalPropertyItem:
    if value in LOGGER_EFFECTIVE_LEVELS_TYPE_0_ADDITIONAL_PROPERTY_ITEM_VALUES:
        return cast(LoggerEffectiveLevelsType0AdditionalPropertyItem, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {LOGGER_EFFECTIVE_LEVELS_TYPE_0_ADDITIONAL_PROPERTY_ITEM_VALUES!r}"
    )
