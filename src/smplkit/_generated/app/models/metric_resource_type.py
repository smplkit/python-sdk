from typing import Literal

MetricResourceType = Literal["metric"]

METRIC_RESOURCE_TYPE_VALUES: set[MetricResourceType] = {
    "metric",
}


def check_metric_resource_type(value: str) -> MetricResourceType:
    if value in METRIC_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {METRIC_RESOURCE_TYPE_VALUES!r}")
