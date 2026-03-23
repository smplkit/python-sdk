from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import Literal

if TYPE_CHECKING:
    from ..models.logger import Logger


T = TypeVar("T", bound="LoggerResource")


@_attrs_define
class LoggerResource:
    """
    Attributes:
        type_ (Literal['logger']):
        attributes (Logger):  Example: {'aliases': ['sequelize'], 'default': 'DEBUG', 'description': 'Controls SQL query
            log verbosity.', 'environments': {}, 'key': 'sql', 'name': 'SQL Logger'}.
        id (None | str | Unset):
    """

    type_: Literal["logger"]
    attributes: Logger
    id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        attributes = self.attributes.to_dict()

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "attributes": attributes,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.logger import Logger

        d = dict(src_dict)
        type_ = cast(Literal["logger"], d.pop("type"))
        if type_ != "logger":
            raise ValueError(f"type must match const 'logger', got '{type_}'")

        attributes = Logger.from_dict(d.pop("attributes"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        logger_resource = cls(
            type_=type_,
            attributes=attributes,
            id=id,
        )

        logger_resource.additional_properties = d
        return logger_resource

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
