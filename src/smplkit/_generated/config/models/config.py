from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from dateutil.parser import isoparse
from typing import cast
import datetime

if TYPE_CHECKING:
    from ..models.config_environments_type_0 import ConfigEnvironmentsType0
    from ..models.config_values_type_0 import ConfigValuesType0


T = TypeVar("T", bound="Config")


@_attrs_define
class Config:
    """
    Example:
        {'created_at': '2026-03-27T10:00:00Z', 'description': 'PostgreSQL connection string', 'environments':
            {'production': {}, 'staging': {}}, 'key': 'database_url', 'name': 'Database URL', 'updated_at':
            '2026-03-27T10:00:00Z', 'values': {'production': 'postgresql://prod-db:5432/smplkit', 'staging':
            'postgresql://staging-db:5432/smplkit_test'}}

    Attributes:
        name (str):
        key (None | str | Unset):
        description (None | str | Unset):
        parent (None | str | Unset):
        values (ConfigValuesType0 | None | Unset):
        environments (ConfigEnvironmentsType0 | None | Unset):
        created_at (datetime.datetime | None | Unset):
        updated_at (datetime.datetime | None | Unset):
    """

    name: str
    key: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    parent: None | str | Unset = UNSET
    values: ConfigValuesType0 | None | Unset = UNSET
    environments: ConfigEnvironmentsType0 | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.config_environments_type_0 import ConfigEnvironmentsType0
        from ..models.config_values_type_0 import ConfigValuesType0

        name = self.name

        key: None | str | Unset
        if isinstance(self.key, Unset):
            key = UNSET
        else:
            key = self.key

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        parent: None | str | Unset
        if isinstance(self.parent, Unset):
            parent = UNSET
        else:
            parent = self.parent

        values: dict[str, Any] | None | Unset
        if isinstance(self.values, Unset):
            values = UNSET
        elif isinstance(self.values, ConfigValuesType0):
            values = self.values.to_dict()
        else:
            values = self.values

        environments: dict[str, Any] | None | Unset
        if isinstance(self.environments, Unset):
            environments = UNSET
        elif isinstance(self.environments, ConfigEnvironmentsType0):
            environments = self.environments.to_dict()
        else:
            environments = self.environments

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        updated_at: None | str | Unset
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
        from ..models.config_environments_type_0 import ConfigEnvironmentsType0
        from ..models.config_values_type_0 import ConfigValuesType0

        d = dict(src_dict)
        name = d.pop("name")

        def _parse_key(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        key = _parse_key(d.pop("key", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_parent(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        parent = _parse_parent(d.pop("parent", UNSET))

        def _parse_values(data: object) -> ConfigValuesType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                values_type_0 = ConfigValuesType0.from_dict(data)

                return values_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ConfigValuesType0 | None | Unset, data)

        values = _parse_values(d.pop("values", UNSET))

        def _parse_environments(data: object) -> ConfigEnvironmentsType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                environments_type_0 = ConfigEnvironmentsType0.from_dict(data)

                return environments_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ConfigEnvironmentsType0 | None | Unset, data)

        environments = _parse_environments(d.pop("environments", UNSET))

        def _parse_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = isoparse(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_updated_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                updated_at_type_0 = isoparse(data)

                return updated_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

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
