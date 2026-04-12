from typing import Literal, cast

CatalogBundleResourceType = Literal["bundle"]

CATALOG_BUNDLE_RESOURCE_TYPE_VALUES: set[CatalogBundleResourceType] = {
    "bundle",
}


def check_catalog_bundle_resource_type(value: str) -> CatalogBundleResourceType:
    if value in CATALOG_BUNDLE_RESOURCE_TYPE_VALUES:
        return cast(CatalogBundleResourceType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CATALOG_BUNDLE_RESOURCE_TYPE_VALUES!r}")
