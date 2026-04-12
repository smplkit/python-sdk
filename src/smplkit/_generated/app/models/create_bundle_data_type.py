from typing import Literal, cast

CreateBundleDataType = Literal["bundle"]

CREATE_BUNDLE_DATA_TYPE_VALUES: set[CreateBundleDataType] = {
    "bundle",
}


def check_create_bundle_data_type(value: str) -> CreateBundleDataType:
    if value in CREATE_BUNDLE_DATA_TYPE_VALUES:
        return cast(CreateBundleDataType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CREATE_BUNDLE_DATA_TYPE_VALUES!r}")
