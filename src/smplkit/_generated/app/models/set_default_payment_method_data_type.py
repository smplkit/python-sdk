from typing import Literal, cast

SetDefaultPaymentMethodDataType = Literal["payment_method"]

SET_DEFAULT_PAYMENT_METHOD_DATA_TYPE_VALUES: set[SetDefaultPaymentMethodDataType] = {
    "payment_method",
}


def check_set_default_payment_method_data_type(value: str) -> SetDefaultPaymentMethodDataType:
    if value in SET_DEFAULT_PAYMENT_METHOD_DATA_TYPE_VALUES:
        return cast(SetDefaultPaymentMethodDataType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SET_DEFAULT_PAYMENT_METHOD_DATA_TYPE_VALUES!r}")
