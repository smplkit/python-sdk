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
    from ..models.config_values_type_0 import ConfigValuesType0
    from ..models.config_environments_type_0 import ConfigEnvironmentsType0


T = TypeVar("T", bound="Config")


@_attrs_define
class Config:
    """
    Example:
        {'description': 'Configuration for the user service.', 'environments': {}, 'key': 'user_service', 'name': 'User
            Service', 'parent': 'c837fa31-9c27-47e6-85e6-6e4c06bcf642', 'values': {'max_retries': 3}}

    Attributes:
        name (str):
        key (Union[None, Unset, str]):
        description (Union[None, Unset, str]):
        parent (Union[None, Unset, str]):
        values (Union['ConfigValuesType0', None, Unset]):
        environments (Union['ConfigEnvironmentsType0', None, Unset]):
        created_at (Union[None, Unset, datetime.datetime]):
        updated_at (Union[None, Unset, datetime.datetime]):
    """

    name: str
    key: Union[None, Unset, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    parent: Union[None, Unset, str] = UNSET
    values: Union["ConfigValuesType0", None, Unset] = UNSET
    environments: Union["ConfigEnvironmentsType0", None, Unset] = UNSET
    created_at: Union[None, Unset, datetime.datetime] = UNSET
    updated_at: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.config_values_type_0 import ConfigValuesType0
        from ..models.config_environments_type_0 import ConfigEnvironmentsType0

        name = self.name

        key: Union[None, Unset, str]
        if isinstance(self.key, Unset):
            key = UNSET
        else:
            key = self.key

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        parent: Union[None, Unset, str]
        if isinstance(self.parent, Unset):
            parent = UNSET
        else:
            parent = self.parent

        values: Union[None, Unset, dict[str, Any]]
        if isinstance(self.values, Unset):
            values = UNSET
        elif isinstance(self.values, ConfigValuesType0):
            values = self.values.to_dict()
        else:
            values = self.values

        environments: Union[None, Unset, dict[str, Any]]
        if isinstance(self.environments, Unset):
            environments = UNSET
        elif isinstance(self.environments, ConfigEnvironmentsType0):
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
        field_dict.update(
            {
                "name": name,
            }
        )
        if key is not UNSET:
            field_dict["key"] = key
        if description is not UNSET:
            field_dict["description"] = description
        if parent is not UNSET:
            field_dict["parent"] = parent
        if values is not UNSET:
            field_dict["values"] = values
        if environments is not UNSET:
            field_dict["environments"] = environments
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.config_values_type_0 import ConfigValuesType0
        from ..models.config_environments_type_0 import ConfigEnvironmentsType0

        d = dict(src_dict)
        name = d.pop("name")

        def _parse_key(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        key = _parse_key(d.pop("key", UNSET))

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_parent(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        parent = _parse_parent(d.pop("parent", UNSET))

        def _parse_values(data: object) -> Union["ConfigValuesType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                values_type_0 = ConfigValuesType0.from_dict(data)

                return values_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ConfigValuesType0", None, Unset], data)

        values = _parse_values(d.pop("values", UNSET))

        def _parse_environments(
            data: object,
        ) -> Union["ConfigEnvironmentsType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                environments_type_0 = ConfigEnvironmentsType0.from_dict(data)

                return environments_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ConfigEnvironmentsType0", None, Unset], data)

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

        config = cls(
            name=name,
            key=key,
            description=description,
            parent=parent,
            values=values,
            environments=environments,
            created_at=created_at,
            updated_at=updated_at,
        )

        config.additional_properties = d
        return config

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
