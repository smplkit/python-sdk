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
    from ..models.flag_environments import FlagEnvironments
    from ..models.flag_sources_type_0_item import FlagSourcesType0Item
    from ..models.flag_value import FlagValue


T = TypeVar("T", bound="Flag")


@_attrs_define
class Flag:
    """
    Example:
        {'created_at': '2026-03-27T10:00:00Z', 'default': False, 'description': 'Enable dark mode for the application
            UI', 'environments': {'production': {'default': False, 'enabled': True, 'rules': [{'description': 'Beta users
            get dark mode', 'logic': {'attribute': 'beta', 'op': 'eq', 'value': True}, 'value': True}]}, 'staging':
            {'default': True, 'enabled': True, 'rules': []}}, 'managed': True, 'name': 'Dark Mode', 'type': 'BOOLEAN',
            'updated_at': '2026-03-27T10:00:00Z', 'values': [{'name': 'on', 'value': True}, {'name': 'off', 'value':
            False}]}

    Attributes:
        name (str): Human-readable display name
        default (Any): Default value; must reference a value in the values array (constrained) or match the flag type
            (unconstrained)
        description (None | str | Unset):
        type_ (None | str | Unset): Value type: STRING, BOOLEAN, NUMERIC, or JSON
        values (list[FlagValue] | None | Unset): Ordered set of allowed values (constrained), or null (unconstrained)
        environments (FlagEnvironments | Unset):
        managed (bool | None | Unset): True if admin-managed, false if auto-discovered
        sources (list[FlagSourcesType0Item] | None | Unset):
        created_at (datetime.datetime | None | Unset):
        updated_at (datetime.datetime | None | Unset):
    """

    name: str
    default: Any
    description: None | str | Unset = UNSET
    type_: None | str | Unset = UNSET
    values: list[FlagValue] | None | Unset = UNSET
    environments: FlagEnvironments | Unset = UNSET
    managed: bool | None | Unset = UNSET
    sources: list[FlagSourcesType0Item] | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        default = self.default

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        type_: None | str | Unset
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        values: list[dict[str, Any]] | None | Unset
        if isinstance(self.values, Unset):
            values = UNSET
        elif isinstance(self.values, list):
            values = []
            for values_type_0_item_data in self.values:
                values_type_0_item = values_type_0_item_data.to_dict()
                values.append(values_type_0_item)

        else:
            values = self.values

        environments: dict[str, Any] | Unset = UNSET
        if not isinstance(self.environments, Unset):
            environments = self.environments.to_dict()

        managed: bool | None | Unset
        if isinstance(self.managed, Unset):
            managed = UNSET
        else:
            managed = self.managed

        sources: list[dict[str, Any]] | None | Unset
        if isinstance(self.sources, Unset):
            sources = UNSET
        elif isinstance(self.sources, list):
            sources = []
            for sources_type_0_item_data in self.sources:
                sources_type_0_item = sources_type_0_item_data.to_dict()
                sources.append(sources_type_0_item)

        else:
            sources = self.sources

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
                "default": default,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if type_ is not UNSET:
            field_dict["type"] = type_
        if values is not UNSET:
            field_dict["values"] = values
        if environments is not UNSET:
            field_dict["environments"] = environments
        if managed is not UNSET:
            field_dict["managed"] = managed
        if sources is not UNSET:
            field_dict["sources"] = sources
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.flag_environments import FlagEnvironments
        from ..models.flag_sources_type_0_item import FlagSourcesType0Item
        from ..models.flag_value import FlagValue

        d = dict(src_dict)
        name = d.pop("name")

        default = d.pop("default")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_type_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        type_ = _parse_type_(d.pop("type", UNSET))

        def _parse_values(data: object) -> list[FlagValue] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                values_type_0 = []
                _values_type_0 = data
                for values_type_0_item_data in _values_type_0:
                    values_type_0_item = FlagValue.from_dict(values_type_0_item_data)

                    values_type_0.append(values_type_0_item)

                return values_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[FlagValue] | None | Unset, data)

        values = _parse_values(d.pop("values", UNSET))

        _environments = d.pop("environments", UNSET)
        environments: FlagEnvironments | Unset
        if isinstance(_environments, Unset):
            environments = UNSET
        else:
            environments = FlagEnvironments.from_dict(_environments)

        def _parse_managed(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        managed = _parse_managed(d.pop("managed", UNSET))

        def _parse_sources(data: object) -> list[FlagSourcesType0Item] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                sources_type_0 = []
                _sources_type_0 = data
                for sources_type_0_item_data in _sources_type_0:
                    sources_type_0_item = FlagSourcesType0Item.from_dict(sources_type_0_item_data)

                    sources_type_0.append(sources_type_0_item)

                return sources_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[FlagSourcesType0Item] | None | Unset, data)

        sources = _parse_sources(d.pop("sources", UNSET))

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

        flag = cls(
            name=name,
            default=default,
            description=description,
            type_=type_,
            values=values,
            environments=environments,
            managed=managed,
            sources=sources,
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
