from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
  from ..models.flag import Flag





T = TypeVar("T", bound="ResourceFlag")



@_attrs_define
class ResourceFlag:
    """ 
        Attributes:
            attributes (Flag):  Example: {'created_at': '2026-03-27T10:00:00Z', 'default': False, 'description': 'Enable
                dark mode for the application UI', 'environments': {'production': {'default': False, 'enabled': True, 'rules':
                [{'description': 'Beta users get dark mode', 'logic': {'attribute': 'beta', 'op': 'eq', 'value': True}, 'value':
                True}]}, 'staging': {'default': True, 'enabled': True, 'rules': []}}, 'key': 'dark_mode', 'name': 'Dark Mode',
                'type': 'BOOLEAN', 'updated_at': '2026-03-27T10:00:00Z', 'values': [{'name': 'on', 'value': True}, {'name':
                'off', 'value': False}]}.
            id (Union[None, Unset, str]):
            type_ (Union[Unset, str]):  Default: ''.
     """

    attributes: 'Flag'
    id: Union[None, Unset, str] = UNSET
    type_: Union[Unset, str] = ''
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.flag import Flag
        attributes = self.attributes.to_dict()

        id: Union[None, Unset, str]
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        type_ = self.type_


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "attributes": attributes,
        })
        if id is not UNSET:
            field_dict["id"] = id
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.flag import Flag
        d = dict(src_dict)
        attributes = Flag.from_dict(d.pop("attributes"))




        def _parse_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        id = _parse_id(d.pop("id", UNSET))


        type_ = d.pop("type", UNSET)

        resource_flag = cls(
            attributes=attributes,
            id=id,
            type_=type_,
        )


        resource_flag.additional_properties = d
        return resource_flag

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
