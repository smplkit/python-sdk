from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field


if TYPE_CHECKING:
    from ..models.bundle_resource import BundleResource


T = TypeVar("T", bound="BundleResponse")


@_attrs_define
class BundleResponse:
    """
    Attributes:
        data (BundleResource):  Example: {'attributes': {'bundle': 'standard', 'plan': 'standard', 'products':
            ['config', 'flags', 'logging'], 'subscriptions': ['sub-uuid-config', 'sub-uuid-flags', 'sub-uuid-logging']},
            'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'type': 'bundle'}.
    """

    data: BundleResource
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
        from ..models.bundle_resource import BundleResource

        d = dict(src_dict)
        data = BundleResource.from_dict(d.pop("data"))

        bundle_response = cls(
            data=data,
        )

        bundle_response.additional_properties = d
        return bundle_response

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
