from typing import Literal

EnvironmentResourceType = Literal["environment"]

ENVIRONMENT_RESOURCE_TYPE_VALUES: set[EnvironmentResourceType] = {
    "environment",
}


def check_environment_resource_type(value: str) -> EnvironmentResourceType:
    if value in ENVIRONMENT_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {ENVIRONMENT_RESOURCE_TYPE_VALUES!r}")
