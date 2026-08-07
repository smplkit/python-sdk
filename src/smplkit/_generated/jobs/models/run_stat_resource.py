from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.run_stat import RunStat


T = TypeVar("T", bound="RunStatResource")


@_attrs_define
class RunStatResource:
    """JSON:API resource envelope for run statistics.

    Example:
        {'attributes': {'buckets': [{'bucket': '2026-06-05T00:00:00Z', 'count': 17}, {'bucket': '2026-06-05T01:00:00Z',
            'count': 25}], 'next_scheduled': {'environment': 'production', 'job': 'nightly_backup', 'job_name': 'Nightly
            database backup', 'scheduled_for': '2026-06-06T02:00:00Z'}, 'recent_failures': [{'created_at':
            '2026-06-05T01:12:00Z', 'failure_reason': 'NON_SUCCESS_STATUS', 'job': 'nightly_backup', 'job_name': 'Nightly
            database backup'}], 'tally': {'canceled': 0, 'failed': 2, 'pending': 1, 'running': 0, 'succeeded': 39}, 'total':
            42}, 'id': 'current', 'type': 'run_stat'}

    Attributes:
        attributes (RunStat): Aggregated run statistics for the requested scope.

            Computed on demand from the account's runs; `total`, `tally`, `buckets`,
            and `recent_failures` honor the request's filters, while `next_scheduled`
            honors only the environment filter (it is forward-looking by definition).
        id (str | Unset):  Default: 'current'.
        type_ (str | Unset):  Default: 'run_stat'.
    """

    attributes: RunStat
    id: str | Unset = "current"
    type_: str | Unset = "run_stat"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attributes = self.attributes.to_dict()

        id = self.id

        type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "attributes": attributes,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_stat import RunStat

        d = dict(src_dict)
        attributes = RunStat.from_dict(d.pop("attributes"))

        id = d.pop("id", UNSET)

        type_ = d.pop("type", UNSET)

        run_stat_resource = cls(
            attributes=attributes,
            id=id,
            type_=type_,
        )

        run_stat_resource.additional_properties = d
        return run_stat_resource

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
