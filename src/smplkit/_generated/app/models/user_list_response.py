from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


if TYPE_CHECKING:
    from ..models.user_list_meta import UserListMeta
    from ..models.user_resource import UserResource


T = TypeVar("T", bound="UserListResponse")


@_attrs_define
class UserListResponse:
    """
    Attributes:
        data (list[UserResource]):
        meta (UserListMeta | Unset):
    """

    data: list[UserResource]
    meta: UserListMeta | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = []
        for data_item_data in self.data:
            data_item = data_item_data.to_dict()
            data.append(data_item)

        meta: dict[str, Any] | Unset = UNSET
        if not isinstance(self.meta, Unset):
            meta = self.meta.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
            }
        )
        if meta is not UNSET:
            field_dict["meta"] = meta

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.user_list_meta import UserListMeta
        from ..models.user_resource import UserResource

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = UserResource.from_dict(data_item_data)

            data.append(data_item)

        _meta = d.pop("meta", UNSET)
        meta: UserListMeta | Unset
        if isinstance(_meta, Unset):
            meta = UNSET
        else:
            meta = UserListMeta.from_dict(_meta)

        user_list_response = cls(
            data=data,
            meta=meta,
        )

        user_list_response.additional_properties = d
        return user_list_response

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
