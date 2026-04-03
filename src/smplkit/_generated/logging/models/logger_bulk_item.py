from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast, Union


T = TypeVar("T", bound="LoggerBulkItem")


@_attrs_define
class LoggerBulkItem:
    """
    Attributes:
        key (str): Normalized logger name
        level (str): Observed log level in smplkit canonical format
        service (Union[None, Unset, str]): Service name that discovered this logger
    """

    key: str
    level: str
    service: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        key = self.key

        level = self.level

        service: Union[None, Unset, str]
        if isinstance(self.service, Unset):
            service = UNSET
        else:
            service = self.service

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "key": key,
                "level": level,
            }
        )
        if service is not UNSET:
            field_dict["service"] = service

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        key = d.pop("key")

        level = d.pop("level")

        def _parse_service(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        service = _parse_service(d.pop("service", UNSET))

        logger_bulk_item = cls(
            key=key,
            level=level,
            service=service,
        )

        logger_bulk_item.additional_properties = d
        return logger_bulk_item

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
