from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field


T = TypeVar("T", bound="WipeTablesSummary")


@_attrs_define
class WipeTablesSummary:
    """
    Attributes:
        audit_event (int):
        audit_event_quota (int):
        forwarder (int):
        forwarder_delivery (int):
        resource_type (int):
        action (int):
    """

    audit_event: int
    audit_event_quota: int
    forwarder: int
    forwarder_delivery: int
    resource_type: int
    action: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        audit_event = self.audit_event

        audit_event_quota = self.audit_event_quota

        forwarder = self.forwarder

        forwarder_delivery = self.forwarder_delivery

        resource_type = self.resource_type

        action = self.action

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "audit_event": audit_event,
                "audit_event_quota": audit_event_quota,
                "forwarder": forwarder,
                "forwarder_delivery": forwarder_delivery,
                "resource_type": resource_type,
                "action": action,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        audit_event = d.pop("audit_event")

        audit_event_quota = d.pop("audit_event_quota")

        forwarder = d.pop("forwarder")

        forwarder_delivery = d.pop("forwarder_delivery")

        resource_type = d.pop("resource_type")

        action = d.pop("action")

        wipe_tables_summary = cls(
            audit_event=audit_event,
            audit_event_quota=audit_event_quota,
            forwarder=forwarder,
            forwarder_delivery=forwarder_delivery,
            resource_type=resource_type,
            action=action,
        )

        wipe_tables_summary.additional_properties = d
        return wipe_tables_summary

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
