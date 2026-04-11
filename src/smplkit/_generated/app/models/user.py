from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from dateutil.parser import isoparse
from typing import cast
import datetime


T = TypeVar("T", bound="User")


@_attrs_define
class User:
    """
    Example:
        {'account': 'd290f1ee-6c54-4b01-90e6-d701748f0851', 'auth_provider': 'GOOGLE', 'created_at':
            '2026-03-20T11:02:16.616Z', 'display_name': 'Jane Smith', 'email': 'jane@example.com', 'email_verified': True,
            'profile_pic': 'https://lh3.googleusercontent.com/a/example', 'role': 'OWNER'}

    Attributes:
        email (str): User's email address
        display_name (str):
        profile_pic (None | str | Unset):
        auth_provider (str | Unset):  Default: ''.
        email_verified (bool | Unset):  Default: False.
        role (None | str | Unset): Role in current account context
        account (str | Unset): Account UUID Default: ''.
        created_at (datetime.datetime | None | Unset):
    """

    email: str
    display_name: str
    profile_pic: None | str | Unset = UNSET
    auth_provider: str | Unset = ""
    email_verified: bool | Unset = False
    role: None | str | Unset = UNSET
    account: str | Unset = ""
    created_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        email = self.email

        display_name = self.display_name

        profile_pic: None | str | Unset
        if isinstance(self.profile_pic, Unset):
            profile_pic = UNSET
        else:
            profile_pic = self.profile_pic

        auth_provider = self.auth_provider

        email_verified = self.email_verified

        role: None | str | Unset
        if isinstance(self.role, Unset):
            role = UNSET
        else:
            role = self.role

        account = self.account

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "email": email,
                "display_name": display_name,
            }
        )
        if profile_pic is not UNSET:
            field_dict["profile_pic"] = profile_pic
        if auth_provider is not UNSET:
            field_dict["auth_provider"] = auth_provider
        if email_verified is not UNSET:
            field_dict["email_verified"] = email_verified
        if role is not UNSET:
            field_dict["role"] = role
        if account is not UNSET:
            field_dict["account"] = account
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        email = d.pop("email")

        display_name = d.pop("display_name")

        def _parse_profile_pic(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        profile_pic = _parse_profile_pic(d.pop("profile_pic", UNSET))

        auth_provider = d.pop("auth_provider", UNSET)

        email_verified = d.pop("email_verified", UNSET)

        def _parse_role(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        role = _parse_role(d.pop("role", UNSET))

        account = d.pop("account", UNSET)

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

        user = cls(
            email=email,
            display_name=display_name,
            profile_pic=profile_pic,
            auth_provider=auth_provider,
            email_verified=email_verified,
            role=role,
            account=account,
            created_at=created_at,
        )

        user.additional_properties = d
        return user

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
