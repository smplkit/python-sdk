from typing import Literal

GroupCreateResourceType = Literal["group"]

GROUP_CREATE_RESOURCE_TYPE_VALUES: set[GroupCreateResourceType] = {
    "group",
}


def check_group_create_resource_type(value: str) -> GroupCreateResourceType:
    if value in GROUP_CREATE_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {GROUP_CREATE_RESOURCE_TYPE_VALUES!r}")
