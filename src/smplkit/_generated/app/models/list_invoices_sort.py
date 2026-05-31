from typing import Literal

ListInvoicesSort = Literal["-created_at", "-status", "-total", "created_at", "status", "total"]

LIST_INVOICES_SORT_VALUES: set[ListInvoicesSort] = {
    "-created_at",
    "-status",
    "-total",
    "created_at",
    "status",
    "total",
}


def check_list_invoices_sort(value: str) -> ListInvoicesSort:
    if value in LIST_INVOICES_SORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_INVOICES_SORT_VALUES!r}")
