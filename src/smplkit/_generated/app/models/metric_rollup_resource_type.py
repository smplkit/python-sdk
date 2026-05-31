from typing import Literal

MetricRollupResourceType = Literal["metric_rollup"]

METRIC_ROLLUP_RESOURCE_TYPE_VALUES: set[MetricRollupResourceType] = {
    "metric_rollup",
}


def check_metric_rollup_resource_type(value: str) -> MetricRollupResourceType:
    if value in METRIC_ROLLUP_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {METRIC_ROLLUP_RESOURCE_TYPE_VALUES!r}")
