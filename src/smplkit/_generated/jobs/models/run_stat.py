from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.run_stat_bucket import RunStatBucket
    from ..models.run_stat_failure import RunStatFailure
    from ..models.run_stat_next_scheduled import RunStatNextScheduled
    from ..models.run_stat_tally import RunStatTally


T = TypeVar("T", bound="RunStat")


@_attrs_define
class RunStat:
    """Aggregated run statistics for the requested scope.

    Computed on demand from the account's runs; `total`, `tally`, `buckets`,
    and `recent_failures` honor the request's filters, while `next_scheduled`
    honors only the environment filter (it is forward-looking by definition).

        Attributes:
            total (int): Runs matching the filters.
            tally (RunStatTally): Run counts by lifecycle state within the requested scope.
            recent_failures (list[RunStatFailure]): The most recently created `FAILED` runs matching the filters, newest
                first — at most 3.
            buckets (list[RunStatBucket] | None | Unset): Run counts over time at the requested `bucket` granularity,
                ordered by bucket start. Only buckets containing at least one run are listed — treat missing buckets as zero.
                `null` when the request did not include the `bucket` directive.
            next_scheduled (None | RunStatNextScheduled | Unset): The soonest `PENDING` run with a fire time at or after the
                request, or `null` when nothing upcoming is scheduled. The `filter[created_at]` range does not apply here — a
                run scheduled long ago for a future fire time is still next.
    """

    total: int
    tally: RunStatTally
    recent_failures: list[RunStatFailure]
    buckets: list[RunStatBucket] | Unset | None = UNSET
    next_scheduled: RunStatNextScheduled | Unset | None = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.run_stat_next_scheduled import RunStatNextScheduled

        total = self.total

        tally = self.tally.to_dict()

        recent_failures = []
        for recent_failures_item_data in self.recent_failures:
            recent_failures_item = recent_failures_item_data.to_dict()
            recent_failures.append(recent_failures_item)

        buckets: list[dict[str, Any]] | Unset | None
        if isinstance(self.buckets, Unset):
            buckets = UNSET
        elif isinstance(self.buckets, list):
            buckets = []
            for buckets_type_0_item_data in self.buckets:
                buckets_type_0_item = buckets_type_0_item_data.to_dict()
                buckets.append(buckets_type_0_item)

        else:
            buckets = self.buckets

        next_scheduled: dict[str, Any] | Unset | None
        if isinstance(self.next_scheduled, Unset):
            next_scheduled = UNSET
        elif isinstance(self.next_scheduled, RunStatNextScheduled):
            next_scheduled = self.next_scheduled.to_dict()
        else:
            next_scheduled = self.next_scheduled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total": total,
                "tally": tally,
                "recent_failures": recent_failures,
            }
        )
        if buckets is not UNSET:
            field_dict["buckets"] = buckets
        if next_scheduled is not UNSET:
            field_dict["next_scheduled"] = next_scheduled

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_stat_bucket import RunStatBucket
        from ..models.run_stat_failure import RunStatFailure
        from ..models.run_stat_next_scheduled import RunStatNextScheduled
        from ..models.run_stat_tally import RunStatTally

        d = dict(src_dict)
        total = d.pop("total")

        tally = RunStatTally.from_dict(d.pop("tally"))

        recent_failures = []
        _recent_failures = d.pop("recent_failures")
        for recent_failures_item_data in _recent_failures:
            recent_failures_item = RunStatFailure.from_dict(recent_failures_item_data)

            recent_failures.append(recent_failures_item)

        def _parse_buckets(data: object) -> list[RunStatBucket] | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                buckets_type_0 = []
                _buckets_type_0 = data
                for buckets_type_0_item_data in _buckets_type_0:
                    buckets_type_0_item = RunStatBucket.from_dict(buckets_type_0_item_data)

                    buckets_type_0.append(buckets_type_0_item)

                return buckets_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[RunStatBucket] | None | Unset, data)

        buckets = _parse_buckets(d.pop("buckets", UNSET))

        def _parse_next_scheduled(data: object) -> RunStatNextScheduled | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                next_scheduled_type_0 = RunStatNextScheduled.from_dict(data)

                return next_scheduled_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunStatNextScheduled | Unset, data)

        next_scheduled = _parse_next_scheduled(d.pop("next_scheduled", UNSET))

        run_stat = cls(
            total=total,
            tally=tally,
            recent_failures=recent_failures,
            buckets=buckets,
            next_scheduled=next_scheduled,
        )

        run_stat.additional_properties = d
        return run_stat

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
