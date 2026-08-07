from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.run_stat_failure_failure_reason_type_0 import (
    RunStatFailureFailureReasonType0,
    check_run_stat_failure_failure_reason_type_0,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="RunStatFailure")


@_attrs_define
class RunStatFailure:
    """One recently failed run.

    Attributes:
        job (str): Key of the job the failed run belongs to.
        created_at (datetime.datetime): When the failed run was created.
        job_name (None | str | Unset): Display name of that job, resolved at read time; `null` when the job no longer
            exists.
        failure_reason (None | RunStatFailureFailureReasonType0 | Unset): Why the run failed; `null` when unrecorded.
    """

    job: str
    created_at: datetime.datetime
    job_name: str | Unset | None = UNSET
    failure_reason: RunStatFailureFailureReasonType0 | Unset | None = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        job = self.job

        created_at = self.created_at.isoformat()

        job_name: str | Unset | None
        if isinstance(self.job_name, Unset):
            job_name = UNSET
        else:
            job_name = self.job_name

        failure_reason: str | Unset | None
        if isinstance(self.failure_reason, Unset):
            failure_reason = UNSET
        elif isinstance(self.failure_reason, str):
            failure_reason = self.failure_reason
        else:
            failure_reason = self.failure_reason

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "job": job,
                "created_at": created_at,
            }
        )
        if job_name is not UNSET:
            field_dict["job_name"] = job_name
        if failure_reason is not UNSET:
            field_dict["failure_reason"] = failure_reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        job = d.pop("job")

        created_at = isoparse(d.pop("created_at"))

        def _parse_job_name(data: object) -> str | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        job_name = _parse_job_name(d.pop("job_name", UNSET))

        def _parse_failure_reason(data: object) -> RunStatFailureFailureReasonType0 | Unset | None:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                failure_reason_type_0 = check_run_stat_failure_failure_reason_type_0(data)

                return failure_reason_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunStatFailureFailureReasonType0 | Unset, data)

        failure_reason = _parse_failure_reason(d.pop("failure_reason", UNSET))

        run_stat_failure = cls(
            job=job,
            created_at=created_at,
            job_name=job_name,
            failure_reason=failure_reason,
        )

        run_stat_failure.additional_properties = d
        return run_stat_failure

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
