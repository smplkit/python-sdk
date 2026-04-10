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
    from ..models.logger_environments_type_0 import LoggerEnvironmentsType0
    from ..models.logger_sources_type_0_item import LoggerSourcesType0Item


T = TypeVar("T", bound="Logger")


@_attrs_define
class Logger:
    """
    Example:
        {'created_at': '2026-04-01T10:00:00Z', 'environments': {'production': {'level': 'WARN'}, 'staging': {'level':
            'DEBUG'}}, 'group': 'database-loggers', 'id': 'com.example.sql', 'level': 'DEBUG', 'managed': True, 'name': 'SQL
            Logger', 'sources': [{'first_observed': '2026-04-01T10:00:00Z', 'service': 'api-gateway'}], 'updated_at':
            '2026-04-01T10:00:00Z'}

    Attributes:
        name (str):
        id (None | str | Unset):
        level (None | str | Unset):
        group (None | str | Unset):
        managed (bool | None | Unset):
        sources (list[LoggerSourcesType0Item] | None | Unset):
        environments (LoggerEnvironmentsType0 | None | Unset):
        created_at (datetime.datetime | None | Unset):
        updated_at (datetime.datetime | None | Unset):
    """

    name: str
    id: None | str | Unset = UNSET
    level: None | str | Unset = UNSET
    group: None | str | Unset = UNSET
    managed: bool | None | Unset = UNSET
    sources: list[LoggerSourcesType0Item] | None | Unset = UNSET
    environments: LoggerEnvironmentsType0 | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.logger_environments_type_0 import LoggerEnvironmentsType0

        name = self.name

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        level: None | str | Unset
        if isinstance(self.level, Unset):
            level = UNSET
        else:
            level = self.level

        group: None | str | Unset
        if isinstance(self.group, Unset):
            group = UNSET
        else:
            group = self.group

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

        environments: dict[str, Any] | None | Unset
        if isinstance(self.environments, Unset):
            environments = UNSET
        elif isinstance(self.environments, LoggerEnvironmentsType0):
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
        if id is not UNSET:
            field_dict["id"] = id
        if level is not UNSET:
            field_dict["level"] = level
        if group is not UNSET:
            field_dict["group"] = group
        if managed is not UNSET:
            field_dict["managed"] = managed
        if sources is not UNSET:
            field_dict["sources"] = sources
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
        from ..models.logger_sources_type_0_item import LoggerSourcesType0Item

        d = dict(src_dict)
        name = d.pop("name")

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_level(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        level = _parse_level(d.pop("level", UNSET))

        def _parse_group(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        group = _parse_group(d.pop("group", UNSET))

        def _parse_managed(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        managed = _parse_managed(d.pop("managed", UNSET))

        def _parse_sources(data: object) -> list[LoggerSourcesType0Item] | None | Unset:
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
                    sources_type_0_item = LoggerSourcesType0Item.from_dict(sources_type_0_item_data)

                    sources_type_0.append(sources_type_0_item)

                return sources_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[LoggerSourcesType0Item] | None | Unset, data)

        sources = _parse_sources(d.pop("sources", UNSET))

        def _parse_environments(data: object) -> LoggerEnvironmentsType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                environments_type_0 = LoggerEnvironmentsType0.from_dict(data)

                return environments_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(LoggerEnvironmentsType0 | None | Unset, data)

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

        logger = cls(
            name=name,
            id=id,
            level=level,
            group=group,
            managed=managed,
            sources=sources,
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
