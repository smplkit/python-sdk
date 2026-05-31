from typing import Literal

EnvironmentCreateResourceType = Literal["environment"]

ENVIRONMENT_CREATE_RESOURCE_TYPE_VALUES: set[EnvironmentCreateResourceType] = {
    "environment",
}


def check_environment_create_resource_type(value: str) -> EnvironmentCreateResourceType:
    if value in ENVIRONMENT_CREATE_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {ENVIRONMENT_CREATE_RESOURCE_TYPE_VALUES!r}")
