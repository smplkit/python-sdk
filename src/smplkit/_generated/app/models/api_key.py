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
    from ..models.api_key_scopes import ApiKeyScopes
    from ..models.api_key_data import ApiKeyData


T = TypeVar("T", bound="ApiKey")


@_attrs_define
class ApiKey:
    """
    Example:
        {'created_at': '2026-03-20T11:02:16.616Z', 'created_by': 'd290f1ee-6c54-4b01-90e6-d701748f0851', 'expires_at':
            '2027-03-20T11:02:16.616Z', 'key': 'sk_api_a1b2c3d4e5f6g7h8i9j0', 'last_used_at': '2026-03-19T08:45:00.000Z',
            'name': 'Production API Key', 'scopes': {}, 'status': 'ACTIVE', 'updated_at': '2026-03-20T11:02:16.616Z'}

    Attributes:
        name (str):
        status (Union[Unset, str]):  Default: ''.
        key (Union[Unset, str]):  Default: ''.
        scopes (Union[Unset, ApiKeyScopes]):
        created_by (Union[Unset, str]):  Default: ''.
        expires_at (Union[None, Unset, datetime.datetime]):
        last_used_at (Union[None, Unset, datetime.datetime]):
        created_at (Union[None, Unset, datetime.datetime]):
        updated_at (Union[None, Unset, datetime.datetime]):
        data (Union[Unset, ApiKeyData]):
    """

    name: str
    status: Union[Unset, str] = ""
    key: Union[Unset, str] = ""
    scopes: Union[Unset, "ApiKeyScopes"] = UNSET
    created_by: Union[Unset, str] = ""
    expires_at: Union[None, Unset, datetime.datetime] = UNSET
    last_used_at: Union[None, Unset, datetime.datetime] = UNSET
    created_at: Union[None, Unset, datetime.datetime] = UNSET
    updated_at: Union[None, Unset, datetime.datetime] = UNSET
    data: Union[Unset, "ApiKeyData"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        status = self.status

        key = self.key

        scopes: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.scopes, Unset):
            scopes = self.scopes.to_dict()

        created_by = self.created_by

        expires_at: Union[None, Unset, str]
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        elif isinstance(self.expires_at, datetime.datetime):
            expires_at = self.expires_at.isoformat()
        else:
            expires_at = self.expires_at

        last_used_at: Union[None, Unset, str]
        if isinstance(self.last_used_at, Unset):
            last_used_at = UNSET
        elif isinstance(self.last_used_at, datetime.datetime):
            last_used_at = self.last_used_at.isoformat()
        else:
            last_used_at = self.last_used_at

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

        data: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if key is not UNSET:
            field_dict["key"] = key
        if scopes is not UNSET:
            field_dict["scopes"] = scopes
        if created_by is not UNSET:
            field_dict["created_by"] = created_by
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at
        if last_used_at is not UNSET:
            field_dict["last_used_at"] = last_used_at
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_key_scopes import ApiKeyScopes
        from ..models.api_key_data import ApiKeyData

        d = dict(src_dict)
        name = d.pop("name")

        status = d.pop("status", UNSET)

        key = d.pop("key", UNSET)

        _scopes = d.pop("scopes", UNSET)
        scopes: Union[Unset, ApiKeyScopes]
        if isinstance(_scopes, Unset):
            scopes = UNSET
        else:
            scopes = ApiKeyScopes.from_dict(_scopes)

        created_by = d.pop("created_by", UNSET)

        def _parse_expires_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                expires_at_type_0 = isoparse(data)

                return expires_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        def _parse_last_used_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_used_at_type_0 = isoparse(data)

                return last_used_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        last_used_at = _parse_last_used_at(d.pop("last_used_at", UNSET))

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

        _data = d.pop("data", UNSET)
        data: Union[Unset, ApiKeyData]
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = ApiKeyData.from_dict(_data)

        api_key = cls(
            name=name,
            status=status,
            key=key,
            scopes=scopes,
            created_by=created_by,
            expires_at=expires_at,
            last_used_at=last_used_at,
            created_at=created_at,
            updated_at=updated_at,
            data=data,
        )

        api_key.additional_properties = d
        return api_key

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
