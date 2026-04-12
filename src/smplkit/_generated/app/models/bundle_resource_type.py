from typing import Literal, cast

BundleResourceType = Literal["bundle"]

BUNDLE_RESOURCE_TYPE_VALUES: set[BundleResourceType] = {
    "bundle",
}


def check_bundle_resource_type(value: str) -> BundleResourceType:
    if value in BUNDLE_RESOURCE_TYPE_VALUES:
        return cast(BundleResourceType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {BUNDLE_RESOURCE_TYPE_VALUES!r}")
