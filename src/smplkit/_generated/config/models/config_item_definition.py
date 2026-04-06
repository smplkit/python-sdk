from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.config_item_definition_type_type_0 import check_config_item_definition_type_type_0
from ..models.config_item_definition_type_type_0 import ConfigItemDefinitionTypeType0
from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union






T = TypeVar("T", bound="ConfigItemDefinition")



@_attrs_define
class ConfigItemDefinition:
    """ Schema for a single config item.

        Attributes:
            value (Any):
            type_ (Union[ConfigItemDefinitionTypeType0, None, Unset]):
            description (Union[None, Unset, str]):
     """

    value: Any
    type_: Union[ConfigItemDefinitionTypeType0, None, Unset] = UNSET
    description: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        value = self.value

        type_: Union[None, Unset, str]
        if isinstance(self.type_, Unset):
            type_ = UNSET
        elif isinstance(self.type_, str):
            type_ = self.type_
        else:
            type_ = self.type_

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "value": value,
        })
        if type_ is not UNSET:
            field_dict["type"] = type_
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        value = d.pop("value")

        def _parse_type_(data: object) -> Union[ConfigItemDefinitionTypeType0, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                type_type_0 = check_config_item_definition_type_type_0(data)



                return type_type_0
            except: # noqa: E722
                pass
            return cast(Union[ConfigItemDefinitionTypeType0, None, Unset], data)

        type_ = _parse_type_(d.pop("type", UNSET))


        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))


        config_item_definition = cls(
            value=value,
            type_=type_,
            description=description,
        )


        config_item_definition.additional_properties = d
        return config_item_definition

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
