from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from dateutil.parser import isoparse
from typing import cast
import datetime


T = TypeVar("T", bound="ShowcaseAccount")


@_attrs_define
class ShowcaseAccount:
    """
    Example:
        {'account_type': 'SHOWCASE', 'api_key': 'sk_api_...', 'created_at': '2026-04-05T14:00:00Z', 'expires_at':
            '2026-04-05T14:01:00Z', 'key': 'showcase-a1b2c3d4', 'name': 'Showcase'}

    Attributes:
        name (str | Unset):  Default: ''.
        key (str | Unset):  Default: ''.
        account_type (str | Unset):  Default: 'SHOWCASE'.
        api_key (str | Unset):  Default: ''.
        expires_at (datetime.datetime | None | Unset):
        created_at (datetime.datetime | None | Unset):
    """

    name: str | Unset = ""
    key: str | Unset = ""
    account_type: str | Unset = "SHOWCASE"
    api_key: str | Unset = ""
    expires_at: datetime.datetime | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        key = self.key

        account_type = self.account_type

        api_key = self.api_key

        expires_at: None | str | Unset
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        elif isinstance(self.expires_at, datetime.datetime):
            expires_at = self.expires_at.isoformat()
        else:
            expires_at = self.expires_at

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if key is not UNSET:
            field_dict["key"] = key
        if account_type is not UNSET:
            field_dict["account_type"] = account_type
        if api_key is not UNSET:
            field_dict["api_key"] = api_key
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        key = d.pop("key", UNSET)

        account_type = d.pop("account_type", UNSET)

        api_key = d.pop("api_key", UNSET)

        def _parse_expires_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                expires_at_type_0 = isoparse(data)

                return expires_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

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

        showcase_account = cls(
            name=name,
            key=key,
            account_type=account_type,
            api_key=api_key,
            expires_at=expires_at,
            created_at=created_at,
        )

        showcase_account.additional_properties = d
        return showcase_account

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
