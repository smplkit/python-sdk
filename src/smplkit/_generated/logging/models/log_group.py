from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
from typing import cast, Union
from typing import Union
import datetime

if TYPE_CHECKING:
  from ..models.log_group_environments_type_0 import LogGroupEnvironmentsType0





T = TypeVar("T", bound="LogGroup")



@_attrs_define
class LogGroup:
    """ 
        Example:
            {'created_at': '2026-04-01T10:00:00Z', 'environments': {'production': {'level': 'ERROR'}}, 'key': 'database-
                loggers', 'level': 'WARN', 'name': 'Database Loggers', 'updated_at': '2026-04-01T10:00:00Z'}

        Attributes:
            name (str):
            key (Union[None, Unset, str]):
            level (Union[None, Unset, str]):
            group (Union[None, Unset, str]):
            environments (Union['LogGroupEnvironmentsType0', None, Unset]):
            created_at (Union[None, Unset, datetime.datetime]):
            updated_at (Union[None, Unset, datetime.datetime]):
     """

    name: str
    key: Union[None, Unset, str] = UNSET
    level: Union[None, Unset, str] = UNSET
    group: Union[None, Unset, str] = UNSET
    environments: Union['LogGroupEnvironmentsType0', None, Unset] = UNSET
    created_at: Union[None, Unset, datetime.datetime] = UNSET
    updated_at: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.log_group_environments_type_0 import LogGroupEnvironmentsType0
        name = self.name

        key: Union[None, Unset, str]
        if isinstance(self.key, Unset):
            key = UNSET
        else:
            key = self.key

        level: Union[None, Unset, str]
        if isinstance(self.level, Unset):
            level = UNSET
        else:
            level = self.level

        group: Union[None, Unset, str]
        if isinstance(self.group, Unset):
            group = UNSET
        else:
            group = self.group

        environments: Union[None, Unset, dict[str, Any]]
        if isinstance(self.environments, Unset):
            environments = UNSET
        elif isinstance(self.environments, LogGroupEnvironmentsType0):
            environments = self.environments.to_dict()
        else:
            environments = self.environments

        created_at: Union[None, Unset, str]
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        updated_at: Union[None, Unset, str]
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        elif isinstance(self.updated_at, datetime.datetime):
            updated_at = self.updated_at.isoformat()
        else:
            updated_at = self.updated_at


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "name": name,
        })
        if key is not UNSET:
            field_dict["key"] = key
        if level is not UNSET:
            field_dict["level"] = level
        if group is not UNSET:
            field_dict["group"] = group
        if environments is not UNSET:
            field_dict["environments"] = environments
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.log_group_environments_type_0 import LogGroupEnvironmentsType0
        d = dict(src_dict)
        name = d.pop("name")

        def _parse_key(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        key = _parse_key(d.pop("key", UNSET))


        def _parse_level(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        level = _parse_level(d.pop("level", UNSET))


        def _parse_group(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        group = _parse_group(d.pop("group", UNSET))


        def _parse_environments(data: object) -> Union['LogGroupEnvironmentsType0', None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                environments_type_0 = LogGroupEnvironmentsType0.from_dict(data)



                return environments_type_0
            except: # noqa: E722
                pass
            return cast(Union['LogGroupEnvironmentsType0', None, Unset], data)

        environments = _parse_environments(d.pop("environments", UNSET))


        def _parse_created_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = isoparse(data)



                return created_at_type_0
            except: # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))


        def _parse_updated_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                updated_at_type_0 = isoparse(data)



                return updated_at_type_0
            except: # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))


        log_group = cls(
            name=name,
            key=key,
            level=level,
            group=group,
            environments=environments,
            created_at=created_at,
            updated_at=updated_at,
        )


        log_group.additional_properties = d
        return log_group

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
