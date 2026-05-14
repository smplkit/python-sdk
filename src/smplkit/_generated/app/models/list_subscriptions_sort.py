from typing import Literal, cast

ListSubscriptionsSort = Literal[
    "-created_at", "-plan", "-product", "-status", "created_at", "plan", "product", "status"
]

LIST_SUBSCRIPTIONS_SORT_VALUES: set[ListSubscriptionsSort] = {
    "-created_at",
    "-plan",
    "-product",
    "-status",
    "created_at",
    "plan",
    "product",
    "status",
}


def check_list_subscriptions_sort(value: str) -> ListSubscriptionsSort:
    if value in LIST_SUBSCRIPTIONS_SORT_VALUES:
        return cast(ListSubscriptionsSort, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_SUBSCRIPTIONS_SORT_VALUES!r}")
