from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from dateutil.parser import isoparse
import datetime

if TYPE_CHECKING:
    from ..models.wipe_tables_summary import WipeTablesSummary


T = TypeVar("T", bound="WipeResponse")


@_attrs_define
class WipeResponse:
    """Summary of a completed wipe action.

    Example:
        {'completed_at': '2026-05-08T19:31:24Z', 'tables': {'action': 11, 'audit_event': 1432, 'audit_event_quota': 5,
            'forwarder': 2, 'forwarder_delivery': 312, 'resource_type': 4}, 'wiped': True}

    Attributes:
        tables (WipeTablesSummary): Counts of records deleted, broken down by record kind.
        completed_at (datetime.datetime): When the wipe completed.
        wiped (bool | Unset): Always `true` for a successful wipe. Default: True.
    """

    tables: WipeTablesSummary
    completed_at: datetime.datetime
    wiped: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        tables = self.tables.to_dict()

        completed_at = self.completed_at.isoformat()

        wiped = self.wiped

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tables": tables,
                "completed_at": completed_at,
            }
        )
        if wiped is not UNSET:
            field_dict["wiped"] = wiped

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.wipe_tables_summary import WipeTablesSummary

        d = dict(src_dict)
        tables = WipeTablesSummary.from_dict(d.pop("tables"))

        completed_at = isoparse(d.pop("completed_at"))

        wiped = d.pop("wiped", UNSET)

        wipe_response = cls(
            tables=tables,
            completed_at=completed_at,
            wiped=wiped,
        )

        wipe_response.additional_properties = d
        return wipe_response

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
