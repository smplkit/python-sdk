from typing import Literal

EnvironmentUsageResourceType = Literal["environment_usage"]

ENVIRONMENT_USAGE_RESOURCE_TYPE_VALUES: set[EnvironmentUsageResourceType] = {
    "environment_usage",
}


def check_environment_usage_resource_type(value: str) -> EnvironmentUsageResourceType:
    if value in ENVIRONMENT_USAGE_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {ENVIRONMENT_USAGE_RESOURCE_TYPE_VALUES!r}")
