from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Literal, cast
from typing import Union

if TYPE_CHECKING:
  from ..models.service import Service





T = TypeVar("T", bound="ServiceResource")



@_attrs_define
class ServiceResource:
    """ 
        Example:
            {'attributes': {'created_at': '2026-03-20T11:02:16.616Z', 'key': 'user_service', 'name': 'User Service',
                'updated_at': '2026-03-20T11:02:16.616Z'}, 'id': 'e5f6a7b8-c9d0-1234-efab-345678901234', 'type': 'service'}

        Attributes:
            type_ (Literal['service']):
            attributes (Service):  Example: {'created_at': '2026-03-20T11:02:16.616Z', 'key': 'user_service', 'name': 'User
                Service', 'updated_at': '2026-03-20T11:02:16.616Z'}.
            id (Union[None, Unset, str]):
     """

    type_: Literal['service']
    attributes: 'Service'
    id: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.service import Service
        type_ = self.type_

        attributes = self.attributes.to_dict()

        id: Union[None, Unset, str]
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "type": type_,
            "attributes": attributes,
        })
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.service import Service
        d = dict(src_dict)
        type_ = cast(Literal['service'] , d.pop("type"))
        if type_ != 'service':
            raise ValueError(f"type must match const 'service', got '{type_}'")

        attributes = Service.from_dict(d.pop("attributes"))




        def _parse_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        id = _parse_id(d.pop("id", UNSET))


        service_resource = cls(
            type_=type_,
            attributes=attributes,
            id=id,
        )


        service_resource.additional_properties = d
        return service_resource

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
