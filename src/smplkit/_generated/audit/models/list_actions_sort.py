from typing import Literal, cast

ListActionsSort = Literal["-key", "key"]

LIST_ACTIONS_SORT_VALUES: set[ListActionsSort] = {
    "-key",
    "key",
}


def check_list_actions_sort(value: str) -> ListActionsSort:
    if value in LIST_ACTIONS_SORT_VALUES:
        return cast(ListActionsSort, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_ACTIONS_SORT_VALUES!r}")
