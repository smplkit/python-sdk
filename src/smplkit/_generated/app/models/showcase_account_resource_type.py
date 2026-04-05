from typing import Literal, cast

ShowcaseAccountResourceType = Literal["showcase_account"]

SHOWCASE_ACCOUNT_RESOURCE_TYPE_VALUES: set[ShowcaseAccountResourceType] = {
    "showcase_account",
}


def check_showcase_account_resource_type(value: str) -> ShowcaseAccountResourceType:
    if value in SHOWCASE_ACCOUNT_RESOURCE_TYPE_VALUES:
        return cast(ShowcaseAccountResourceType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOWCASE_ACCOUNT_RESOURCE_TYPE_VALUES!r}")
