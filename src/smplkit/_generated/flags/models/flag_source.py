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
    from ..models.flag_source_data_type_0 import FlagSourceDataType0


T = TypeVar("T", bound="FlagSource")


@_attrs_define
class FlagSource:
    """
    Example:
        {'created_at': '2026-04-17T10:00:00Z', 'data': {'default': True, 'type': 'BOOLEAN'}, 'environment':
            'production', 'first_observed': '2026-04-17T10:00:00Z', 'last_seen': '2026-04-17T15:30:00Z', 'service': 'api-
            gateway', 'updated_at': '2026-04-17T15:30:00Z'}

    Attributes:
        service (str | Unset):
        environment (str | Unset):
        first_observed (datetime.datetime | None | Unset):
        last_seen (datetime.datetime | None | Unset):
        data (FlagSourceDataType0 | None | Unset):
        created_at (datetime.datetime | None | Unset):
        updated_at (datetime.datetime | None | Unset):
    """

    service: str | Unset = UNSET
    environment: str | Unset = UNSET
    first_observed: datetime.datetime | None | Unset = UNSET
    last_seen: datetime.datetime | None | Unset = UNSET
    data: FlagSourceDataType0 | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.flag_source_data_type_0 import FlagSourceDataType0

        service = self.service

        environment = self.environment

        first_observed: None | str | Unset
        if isinstance(self.first_observed, Unset):
            first_observed = UNSET
        elif isinstance(self.first_observed, datetime.datetime):
            first_observed = self.first_observed.isoformat()
        else:
            first_observed = self.first_observed

        last_seen: None | str | Unset
        if isinstance(self.last_seen, Unset):
            last_seen = UNSET
        elif isinstance(self.last_seen, datetime.datetime):
            last_seen = self.last_seen.isoformat()
        else:
            last_seen = self.last_seen

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, FlagSourceDataType0):
            data = self.data.to_dict()
        else:
            data = self.data

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
        field_dict.update({})
        if service is not UNSET:
            field_dict["service"] = service
        if environment is not UNSET:
            field_dict["environment"] = environment
        if first_observed is not UNSET:
            field_dict["first_observed"] = first_observed
        if last_seen is not UNSET:
            field_dict["last_seen"] = last_seen
        if data is not UNSET:
            field_dict["data"] = data
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.flag_source_data_type_0 import FlagSourceDataType0

        d = dict(src_dict)
        service = d.pop("service", UNSET)

        environment = d.pop("environment", UNSET)

        def _parse_first_observed(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                first_observed_type_0 = isoparse(data)

                return first_observed_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        first_observed = _parse_first_observed(d.pop("first_observed", UNSET))

        def _parse_last_seen(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_seen_type_0 = isoparse(data)

                return last_seen_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        last_seen = _parse_last_seen(d.pop("last_seen", UNSET))

        def _parse_data(data: object) -> FlagSourceDataType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = FlagSourceDataType0.from_dict(data)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FlagSourceDataType0 | None | Unset, data)

        data = _parse_data(d.pop("data", UNSET))

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

        flag_source = cls(
            service=service,
            environment=environment,
            first_observed=first_observed,
            last_seen=last_seen,
            data=data,
            created_at=created_at,
            updated_at=updated_at,
        )

        flag_source.additional_properties = d
        return flag_source

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
