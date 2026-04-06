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
  from ..models.logger import Logger





T = TypeVar("T", bound="ResourceLogger")



@_attrs_define
class ResourceLogger:
    """ 
        Attributes:
            attributes (Logger):  Example: {'created_at': '2026-04-01T10:00:00Z', 'environments': {'production': {'level':
                'WARN'}, 'staging': {'level': 'DEBUG'}}, 'group': '550e8400-e29b-41d4-a716-446655440000', 'key':
                'com.example.sql', 'level': 'DEBUG', 'managed': True, 'name': 'SQL Logger', 'sources': [{'first_observed':
                '2026-04-01T10:00:00Z', 'service': 'api-gateway'}], 'updated_at': '2026-04-01T10:00:00Z'}.
            id (Union[None, Unset, str]):
            type_ (Union[Unset, str]):  Default: ''.
     """

    attributes: 'Logger'
    id: Union[None, Unset, str] = UNSET
    type_: Union[Unset, str] = ''
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.logger import Logger
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
        from ..models.logger import Logger
        d = dict(src_dict)
        attributes = Logger.from_dict(d.pop("attributes"))




        def _parse_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        id = _parse_id(d.pop("id", UNSET))


        type_ = d.pop("type", UNSET)

        resource_logger = cls(
            attributes=attributes,
            id=id,
            type_=type_,
        )


        resource_logger.additional_properties = d
        return resource_logger

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
