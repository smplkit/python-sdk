from typing import Literal

ListMetricNamesSort = Literal["-name", "name"]

LIST_METRIC_NAMES_SORT_VALUES: set[ListMetricNamesSort] = {
    "-name",
    "name",
}


def check_list_metric_names_sort(value: str) -> ListMetricNamesSort:
    if value in LIST_METRIC_NAMES_SORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_METRIC_NAMES_SORT_VALUES!r}")
