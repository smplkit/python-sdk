from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field


if TYPE_CHECKING:
    from ..models.showcase_account_resource import ShowcaseAccountResource


T = TypeVar("T", bound="ShowcaseAccountResponse")


@_attrs_define
class ShowcaseAccountResponse:
    """
    Attributes:
        data (ShowcaseAccountResource):  Example: {'attributes': {'account_type': 'SHOWCASE', 'api_key': 'sk_api_...',
            'created_at': '2026-04-05T14:00:00Z', 'expires_at': '2026-04-05T14:01:00Z', 'key': 'showcase-a1b2c3d4', 'name':
            'Showcase'}, 'id': 'd290f1ee-6c54-4b01-90e6-d701748f0851', 'type': 'showcase_account'}.
    """

    data: ShowcaseAccountResource
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
        from ..models.showcase_account_resource import ShowcaseAccountResource

        d = dict(src_dict)
        data = ShowcaseAccountResource.from_dict(d.pop("data"))

        showcase_account_response = cls(
            data=data,
        )

        showcase_account_response.additional_properties = d
        return showcase_account_response

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
