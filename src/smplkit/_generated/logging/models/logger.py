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
    from ..models.logger_environments_type_0 import LoggerEnvironmentsType0


T = TypeVar("T", bound="Logger")


@_attrs_define
class Logger:
    """
    Example:
        {'aliases': ['sequelize'], 'default': 'DEBUG', 'description': 'Controls SQL query log verbosity.',
            'environments': {}, 'key': 'sql', 'name': 'SQL Logger'}

    Attributes:
        name (str):
        default (str):
        key (Union[None, Unset, str]):
        description (Union[None, Unset, str]):
        aliases (Union[None, Unset, list[str]]):
        environments (Union['LoggerEnvironmentsType0', None, Unset]):
        created_at (Union[None, Unset, datetime.datetime]):
        updated_at (Union[None, Unset, datetime.datetime]):
    """

    name: str
    default: str
    key: Union[None, Unset, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    aliases: Union[None, Unset, list[str]] = UNSET
    environments: Union["LoggerEnvironmentsType0", None, Unset] = UNSET
    created_at: Union[None, Unset, datetime.datetime] = UNSET
    updated_at: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.logger_environments_type_0 import LoggerEnvironmentsType0

        name = self.name

        default = self.default

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

        aliases: Union[None, Unset, list[str]]
        if isinstance(self.aliases, Unset):
            aliases = UNSET
        elif isinstance(self.aliases, list):
            aliases = self.aliases

        else:
            aliases = self.aliases

        environments: Union[None, Unset, dict[str, Any]]
        if isinstance(self.environments, Unset):
            environments = UNSET
        elif isinstance(self.environments, LoggerEnvironmentsType0):
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
                "default": default,
            }
        )
        if key is not UNSET:
            field_dict["key"] = key
        if description is not UNSET:
            field_dict["description"] = description
        if aliases is not UNSET:
            field_dict["aliases"] = aliases
        if environments is not UNSET:
            field_dict["environments"] = environments
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.logger_environments_type_0 import LoggerEnvironmentsType0

        d = dict(src_dict)
        name = d.pop("name")

        default = d.pop("default")

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

        def _parse_aliases(data: object) -> Union[None, Unset, list[str]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                aliases_type_0 = cast(list[str], data)

                return aliases_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str]], data)

        aliases = _parse_aliases(d.pop("aliases", UNSET))

        def _parse_environments(
            data: object,
        ) -> Union["LoggerEnvironmentsType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                environments_type_0 = LoggerEnvironmentsType0.from_dict(data)

                return environments_type_0
            except:  # noqa: E722
                pass
            return cast(Union["LoggerEnvironmentsType0", None, Unset], data)

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

        logger = cls(
            name=name,
            default=default,
            key=key,
            description=description,
            aliases=aliases,
            environments=environments,
            created_at=created_at,
            updated_at=updated_at,
        )

        logger.additional_properties = d
        return logger

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
