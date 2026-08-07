from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.run_stat_resource import RunStatResource


T = TypeVar("T", bound="RunStatsResponse")


@_attrs_define
class RunStatsResponse:
    """JSON:API single-resource response for run statistics.

    Attributes:
        data (RunStatResource): JSON:API resource envelope for run statistics. Example: {'attributes': {'buckets':
            [{'bucket': '2026-06-05T00:00:00Z', 'count': 17}, {'bucket': '2026-06-05T01:00:00Z', 'count': 25}],
            'next_scheduled': {'environment': 'production', 'job': 'nightly_backup', 'job_name': 'Nightly database backup',
            'scheduled_for': '2026-06-06T02:00:00Z'}, 'recent_failures': [{'created_at': '2026-06-05T01:12:00Z',
            'failure_reason': 'NON_SUCCESS_STATUS', 'job': 'nightly_backup', 'job_name': 'Nightly database backup'}],
            'tally': {'canceled': 0, 'failed': 2, 'pending': 1, 'running': 0, 'succeeded': 39}, 'total': 42}, 'id':
            'current', 'type': 'run_stat'}.
    """

    data: RunStatResource
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_stat_resource import RunStatResource

        d = dict(src_dict)
        data = RunStatResource.from_dict(d.pop("data"))

        run_stats_response = cls(
            data=data,
        )

        run_stats_response.additional_properties = d
        return run_stats_response

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
