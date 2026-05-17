from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.search_events_request_filter_type_0 import SearchEventsRequestFilterType0


T = TypeVar("T", bound="SearchEventsRequest")


@_attrs_define
class SearchEventsRequest:
    """Request body for ``POST /api/v1/search/events``.

    Mirrors every column filter accepted by ``GET /api/v1/events`` with
    identical semantics, and adds a top-level ``filter`` field carrying
    a JSON Logic expression. When ``filter`` is present the search is
    silently capped to the last 30 days by ``occurred_at``; the
    expression is then evaluated in memory against each row that passes
    the column filters using the same ``json-logic-qubit`` evaluator
    that runs in the forwarder pipeline (so search results match what
    would be forwarded).

    Filter-combination rules match ``GET /api/v1/events`` exactly:

    - ``filter[resource_id]`` must be accompanied by
      ``filter[resource_type]`` — the index is keyed on the pair.
    - ``filter[search]`` must be accompanied by either
      ``filter[occurred_at]`` or ``filter[resource_type]`` +
      ``filter[resource_id]`` — substring matching has no index, so an
      unbounded substring scan is rejected.

        Attributes:
            filter_ (None | SearchEventsRequestFilterType0 | Unset): Optional JSON Logic expression evaluated against each
                row after column filters narrow the candidate set. Null, absent, or an empty object disables JSON Logic
                filtering. When present, the search is silently capped to the last 30 days by `occurred_at` (intersected with
                any explicit `filter[occurred_at]` the caller supplied).
            filteraction (None | str | Unset): Exact match on the event's `action` field.
            filterresource_type (None | str | Unset): Exact match on the event's `resource_type` field.
            filterresource_id (None | str | Unset): Exact match on the event's `resource_id` field. Must be accompanied by
                `filter[resource_type]`.
            filteractor_type (None | str | Unset): Exact match on the event's `actor_type` field.
            filteractor_id (None | str | Unset): Exact match on the event's `actor_id` field.
            filteroccurred_at (None | str | Unset): Date range using interval notation, e.g.
                `[2026-04-01T00:00:00Z,2026-04-15T00:00:00Z)`. Required by `filter[search]` when the resource pair isn't
                provided. When a JSON Logic `filter` is present, the effective range is intersected with the last 30 days.
            filtersearch (None | str | Unset): Case-insensitive substring match on `resource_id` or `description`. Must be
                accompanied by either `filter[occurred_at]` or `filter[resource_type]` + `filter[resource_id]`.
            pagesize (int | Unset): Maximum events to return. Range 1..1000, default 10. The default is intentionally
                smaller than the list endpoint's default of 1000 because the search UI typically renders results one card at a
                time. Default: 10.
            pageafter (None | str | Unset): Opaque cursor — pass the previous response's `links.next` cursor verbatim to
                fetch the next page. Keep the same `sort` value across paginated requests.
            sort (str | Unset): Sort field: `occurred_at` or `created_at`, optionally prefixed with `-` for descending
                order. Default `-occurred_at` (newest first). Default: '-occurred_at'.
    """

    filter_: None | SearchEventsRequestFilterType0 | Unset = UNSET
    filteraction: None | str | Unset = UNSET
    filterresource_type: None | str | Unset = UNSET
    filterresource_id: None | str | Unset = UNSET
    filteractor_type: None | str | Unset = UNSET
    filteractor_id: None | str | Unset = UNSET
    filteroccurred_at: None | str | Unset = UNSET
    filtersearch: None | str | Unset = UNSET
    pagesize: int | Unset = 10
    pageafter: None | str | Unset = UNSET
    sort: str | Unset = "-occurred_at"

    def to_dict(self) -> dict[str, Any]:
        from ..models.search_events_request_filter_type_0 import SearchEventsRequestFilterType0

        filter_: dict[str, Any] | None | Unset
        if isinstance(self.filter_, Unset):
            filter_ = UNSET
        elif isinstance(self.filter_, SearchEventsRequestFilterType0):
            filter_ = self.filter_.to_dict()
        else:
            filter_ = self.filter_

        filteraction: None | str | Unset
        if isinstance(self.filteraction, Unset):
            filteraction = UNSET
        else:
            filteraction = self.filteraction

        filterresource_type: None | str | Unset
        if isinstance(self.filterresource_type, Unset):
            filterresource_type = UNSET
        else:
            filterresource_type = self.filterresource_type

        filterresource_id: None | str | Unset
        if isinstance(self.filterresource_id, Unset):
            filterresource_id = UNSET
        else:
            filterresource_id = self.filterresource_id

        filteractor_type: None | str | Unset
        if isinstance(self.filteractor_type, Unset):
            filteractor_type = UNSET
        else:
            filteractor_type = self.filteractor_type

        filteractor_id: None | str | Unset
        if isinstance(self.filteractor_id, Unset):
            filteractor_id = UNSET
        else:
            filteractor_id = self.filteractor_id

        filteroccurred_at: None | str | Unset
        if isinstance(self.filteroccurred_at, Unset):
            filteroccurred_at = UNSET
        else:
            filteroccurred_at = self.filteroccurred_at

        filtersearch: None | str | Unset
        if isinstance(self.filtersearch, Unset):
            filtersearch = UNSET
        else:
            filtersearch = self.filtersearch

        pagesize = self.pagesize

        pageafter: None | str | Unset
        if isinstance(self.pageafter, Unset):
            pageafter = UNSET
        else:
            pageafter = self.pageafter

        sort = self.sort

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if filter_ is not UNSET:
            field_dict["filter"] = filter_
        if filteraction is not UNSET:
            field_dict["filter[action]"] = filteraction
        if filterresource_type is not UNSET:
            field_dict["filter[resource_type]"] = filterresource_type
        if filterresource_id is not UNSET:
            field_dict["filter[resource_id]"] = filterresource_id
        if filteractor_type is not UNSET:
            field_dict["filter[actor_type]"] = filteractor_type
        if filteractor_id is not UNSET:
            field_dict["filter[actor_id]"] = filteractor_id
        if filteroccurred_at is not UNSET:
            field_dict["filter[occurred_at]"] = filteroccurred_at
        if filtersearch is not UNSET:
            field_dict["filter[search]"] = filtersearch
        if pagesize is not UNSET:
            field_dict["page[size]"] = pagesize
        if pageafter is not UNSET:
            field_dict["page[after]"] = pageafter
        if sort is not UNSET:
            field_dict["sort"] = sort

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.search_events_request_filter_type_0 import SearchEventsRequestFilterType0

        d = dict(src_dict)

        def _parse_filter_(data: object) -> None | SearchEventsRequestFilterType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                filter_type_0 = SearchEventsRequestFilterType0.from_dict(data)

                return filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SearchEventsRequestFilterType0 | Unset, data)

        filter_ = _parse_filter_(d.pop("filter", UNSET))

        def _parse_filteraction(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filteraction = _parse_filteraction(d.pop("filter[action]", UNSET))

        def _parse_filterresource_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filterresource_type = _parse_filterresource_type(d.pop("filter[resource_type]", UNSET))

        def _parse_filterresource_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filterresource_id = _parse_filterresource_id(d.pop("filter[resource_id]", UNSET))

        def _parse_filteractor_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filteractor_type = _parse_filteractor_type(d.pop("filter[actor_type]", UNSET))

        def _parse_filteractor_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filteractor_id = _parse_filteractor_id(d.pop("filter[actor_id]", UNSET))

        def _parse_filteroccurred_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filteroccurred_at = _parse_filteroccurred_at(d.pop("filter[occurred_at]", UNSET))

        def _parse_filtersearch(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filtersearch = _parse_filtersearch(d.pop("filter[search]", UNSET))

        pagesize = d.pop("page[size]", UNSET)

        def _parse_pageafter(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        pageafter = _parse_pageafter(d.pop("page[after]", UNSET))

        sort = d.pop("sort", UNSET)

        search_events_request = cls(
            filter_=filter_,
            filteraction=filteraction,
            filterresource_type=filterresource_type,
            filterresource_id=filterresource_id,
            filteractor_type=filteractor_type,
            filteractor_id=filteractor_id,
            filteroccurred_at=filteroccurred_at,
            filtersearch=filtersearch,
            pagesize=pagesize,
            pageafter=pageafter,
            sort=sort,
        )

        return search_events_request
