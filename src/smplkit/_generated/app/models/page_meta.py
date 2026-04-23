from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field


T = TypeVar("T", bound="PageMeta")


@_attrs_define
class PageMeta:
    """
    Attributes:
        size (int): Page size used for this response
        number (int): 1-based page number returned
        total_items (int): Total number of matching items across all pages
        total_pages (int): Total number of pages at the current page size
    """

    size: int
    number: int
    total_items: int
    total_pages: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        size = self.size

        number = self.number

        total_items = self.total_items

        total_pages = self.total_pages

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "size": size,
                "number": number,
                "total_items": total_items,
                "total_pages": total_pages,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        size = d.pop("size")

        number = d.pop("number")

        total_items = d.pop("total_items")

        total_pages = d.pop("total_pages")

        page_meta = cls(
            size=size,
            number=number,
            total_items=total_items,
            total_pages=total_pages,
        )

        page_meta.additional_properties = d
        return page_meta

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
