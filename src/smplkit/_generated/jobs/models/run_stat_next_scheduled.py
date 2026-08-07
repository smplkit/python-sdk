from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="RunStatNextScheduled")


@_attrs_define
class RunStatNextScheduled:
    """The soonest upcoming scheduled run.

    Attributes:
        job (str): Key of the job the run belongs to.
        scheduled_for (datetime.datetime): The intended fire time.
        environment (str): Environment the run will execute in.
        job_name (None | str | Unset): Display name of that job, resolved at read time; `null` when the job no longer
            exists.
    """

    job: str
    scheduled_for: datetime.datetime
    environment: str
    job_name: str | Unset | None = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        job = self.job

        scheduled_for = self.scheduled_for.isoformat()

        environment = self.environment

        job_name: str | Unset | None
        if isinstance(self.job_name, Unset):
            job_name = UNSET
        else:
            job_name = self.job_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "job": job,
                "scheduled_for": scheduled_for,
                "environment": environment,
            }
        )
        if job_name is not UNSET:
            field_dict["job_name"] = job_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        job = d.pop("job")

        scheduled_for = isoparse(d.pop("scheduled_for"))

        environment = d.pop("environment")

        def _parse_job_name(data: object) -> str | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        job_name = _parse_job_name(d.pop("job_name", UNSET))

        run_stat_next_scheduled = cls(
            job=job,
            scheduled_for=scheduled_for,
            environment=environment,
            job_name=job_name,
        )

        run_stat_next_scheduled.additional_properties = d
        return run_stat_next_scheduled

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
