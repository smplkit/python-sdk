from typing import Literal, cast

GetRunStatsBucketType0 = Literal["15m", "1d", "1h", "1m", "5m", "6h"]

GET_RUN_STATS_BUCKET_TYPE_0_VALUES: set[GetRunStatsBucketType0] = {
    "15m",
    "1d",
    "1h",
    "1m",
    "5m",
    "6h",
}


def check_get_run_stats_bucket_type_0(value: str) -> GetRunStatsBucketType0:
    if value in GET_RUN_STATS_BUCKET_TYPE_0_VALUES:
        return cast(GetRunStatsBucketType0, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {GET_RUN_STATS_BUCKET_TYPE_0_VALUES!r}")
