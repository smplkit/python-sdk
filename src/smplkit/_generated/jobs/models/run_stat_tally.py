from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RunStatTally")


@_attrs_define
class RunStatTally:
    """Run counts by lifecycle state within the requested scope.

    Attributes:
        pending (int): Runs in status `PENDING`.
        running (int): Runs in status `RUNNING`.
        succeeded (int): Runs in status `SUCCEEDED`.
        failed (int): Runs in status `FAILED`.
        canceled (int): Runs in status `CANCELED`.
    """

    pending: int
    running: int
    succeeded: int
    failed: int
    canceled: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        pending = self.pending

        running = self.running

        succeeded = self.succeeded

        failed = self.failed

        canceled = self.canceled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "pending": pending,
                "running": running,
                "succeeded": succeeded,
                "failed": failed,
                "canceled": canceled,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        pending = d.pop("pending")

        running = d.pop("running")

        succeeded = d.pop("succeeded")

        failed = d.pop("failed")

        canceled = d.pop("canceled")

        run_stat_tally = cls(
            pending=pending,
            running=running,
            succeeded=succeeded,
            failed=failed,
            canceled=canceled,
        )

        run_stat_tally.additional_properties = d
        return run_stat_tally

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
