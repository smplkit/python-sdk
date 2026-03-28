from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from dateutil.parser import isoparse
from typing import cast
from typing import Union
import datetime

if TYPE_CHECKING:
    from ..models.flag_value import FlagValue
    from ..models.flag_environments import FlagEnvironments


T = TypeVar("T", bound="Flag")


@_attrs_define
class Flag:
    """
    Example:
        {'created_at': '2026-03-27T10:00:00Z', 'default': False, 'description': 'Enable dark mode for the application
            UI', 'environments': {'production': {'default': False, 'enabled': True, 'rules': [{'description': 'Beta users
            get dark mode', 'logic': {'attribute': 'beta', 'op': 'eq', 'value': True}, 'value': True}]}, 'staging':
            {'default': True, 'enabled': True, 'rules': []}}, 'key': 'dark_mode', 'name': 'Dark Mode', 'type': 'BOOLEAN',
            'updated_at': '2026-03-27T10:00:00Z', 'values': [{'name': 'on', 'value': True}, {'name': 'off', 'value':
            False}]}

    Attributes:
        key (str): Unique key within account
        name (str): Human-readable display name
        type_ (str): Value type: STRING, BOOLEAN, NUMERIC, or JSON
        default (Any): Default value; must reference a value in the values array
        values (list['FlagValue']): Closed set of possible values
        description (Union[None, Unset, str]):
        environments (Union[Unset, FlagEnvironments]):
        created_at (Union[None, Unset, datetime.datetime]):
        updated_at (Union[None, Unset, datetime.datetime]):
    """

    key: str
    name: str
    type_: str
    default: Any
    values: list["FlagValue"]
    description: Union[None, Unset, str] = UNSET
    environments: Union[Unset, "FlagEnvironments"] = UNSET
    created_at: Union[None, Unset, datetime.datetime] = UNSET
    updated_at: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        key = self.key

        name = self.name

        type_ = self.type_

        default = self.default

        values = []
        for values_item_data in self.values:
            values_item = values_item_data.to_dict()
            values.append(values_item)

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        environments: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.environments, Unset):
            environments = self.environments.to_dict()

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
        field_dict.update(
            {
                "key": key,
                "name": name,
                "type": type_,
                "default": default,
                "values": values,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if environments is not UNSET:
            field_dict["environments"] = environments
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.flag_value import FlagValue
        from ..models.flag_environments import FlagEnvironments

        d = dict(src_dict)
        key = d.pop("key")

        name = d.pop("name")

        type_ = d.pop("type")

        default = d.pop("default")

        values = []
        _values = d.pop("values")
        for values_item_data in _values:
            values_item = FlagValue.from_dict(values_item_data)

            values.append(values_item)

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        _environments = d.pop("environments", UNSET)
        environments: Union[Unset, FlagEnvironments]
        if isinstance(_environments, Unset):
            environments = UNSET
        else:
            environments = FlagEnvironments.from_dict(_environments)

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
            except:  # noqa: E722
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
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        flag = cls(
            key=key,
            name=name,
            type_=type_,
            default=default,
            values=values,
            description=description,
            environments=environments,
            created_at=created_at,
            updated_at=updated_at,
        )

        flag.additional_properties = d
        return flag

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
