from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.config import Config


T = TypeVar("T", bound="ResourceConfig")


@_attrs_define
class ResourceConfig:
    """
    Attributes:
        attributes (Config):  Example: {'created_at': '2026-03-27T10:00:00Z', 'description': 'PostgreSQL connection
            string', 'environments': {'production': {}, 'staging': {}}, 'key': 'database_url', 'name': 'Database URL',
            'updated_at': '2026-03-27T10:00:00Z', 'values': {'production': 'postgresql://prod-db:5432/smplkit', 'staging':
            'postgresql://staging-db:5432/smplkit_test'}}.
        id (None | str | Unset):
        type_ (str | Unset):  Default: ''.
    """

    attributes: Config
    id: None | str | Unset = UNSET
    type_: str | Unset = ""
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attributes = self.attributes.to_dict()

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "attributes": attributes,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.config import Config

        d = dict(src_dict)
        attributes = Config.from_dict(d.pop("attributes"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        type_ = d.pop("type", UNSET)

        resource_config = cls(
            attributes=attributes,
            id=id,
            type_=type_,
        )

        resource_config.additional_properties = d
        return resource_config

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
