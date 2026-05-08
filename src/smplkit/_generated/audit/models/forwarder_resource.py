from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


if TYPE_CHECKING:
    from ..models.forwarder import Forwarder


T = TypeVar("T", bound="ForwarderResource")


@_attrs_define
class ForwarderResource:
    """
    Example:
        {'attributes': {'created_at': '2026-05-07T12:00:00Z', 'data': {}, 'enabled': True, 'filter': {'==': [{'var':
            'action'}, 'user.created']}, 'forwarder_type': 'datadog', 'http': {'headers': [{'name': 'DD-API-KEY', 'value':
            'dd-api-key-plaintext'}], 'method': 'POST', 'success_status': '2xx', 'url': 'https://http-
            intake.logs.datadoghq.com/api/v2/logs'}, 'name': 'Datadog production', 'slug': 'datadog_production',
            'updated_at': '2026-05-07T12:00:00Z', 'version': 1}, 'id': '11111111-2222-3333-4444-555555555555', 'type':
            'forwarder'}

    Attributes:
        id (str):
        attributes (Forwarder): Public-facing forwarder resource.

            Attribute set on POST /api/v1/forwarders:
                - name (required)
                - forwarder_type (required)
                - http (required)
                - enabled (optional, defaults true)
                - filter (optional, JSON Logic)
                - transform (optional, JSONata)

            The slug is server-derived from name on create; it is immutable on
            update because consumers (UI, observability) key off it.
        type_ (str | Unset):  Default: 'forwarder'.
    """

    id: str
    attributes: Forwarder
    type_: str | Unset = "forwarder"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        attributes = self.attributes.to_dict()

        type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "attributes": attributes,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.forwarder import Forwarder

        d = dict(src_dict)
        id = d.pop("id")

        attributes = Forwarder.from_dict(d.pop("attributes"))

        type_ = d.pop("type", UNSET)

        forwarder_resource = cls(
            id=id,
            attributes=attributes,
            type_=type_,
        )

        forwarder_resource.additional_properties = d
        return forwarder_resource

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
