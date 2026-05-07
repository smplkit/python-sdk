from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.forwarder_list_links import ForwarderListLinks
    from ..models.forwarder_list_meta import ForwarderListMeta
    from ..models.forwarder_resource import ForwarderResource


T = TypeVar("T", bound="ForwarderListResponse")


@_attrs_define
class ForwarderListResponse:
    """
    Attributes:
        data (list[ForwarderResource]):
        meta (ForwarderListMeta):
        links (ForwarderListLinks | None | Unset):
    """

    data: list[ForwarderResource]
    meta: ForwarderListMeta
    links: ForwarderListLinks | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.forwarder_list_links import ForwarderListLinks

        data = []
        for data_item_data in self.data:
            data_item = data_item_data.to_dict()
            data.append(data_item)

        meta = self.meta.to_dict()

        links: dict[str, Any] | None | Unset
        if isinstance(self.links, Unset):
            links = UNSET
        elif isinstance(self.links, ForwarderListLinks):
            links = self.links.to_dict()
        else:
            links = self.links

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
                "meta": meta,
            }
        )
        if links is not UNSET:
            field_dict["links"] = links

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.forwarder_list_links import ForwarderListLinks
        from ..models.forwarder_list_meta import ForwarderListMeta
        from ..models.forwarder_resource import ForwarderResource

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = ForwarderResource.from_dict(data_item_data)

            data.append(data_item)

        meta = ForwarderListMeta.from_dict(d.pop("meta"))

        def _parse_links(data: object) -> ForwarderListLinks | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                links_type_0 = ForwarderListLinks.from_dict(data)

                return links_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ForwarderListLinks | None | Unset, data)

        links = _parse_links(d.pop("links", UNSET))

        forwarder_list_response = cls(
            data=data,
            meta=meta,
            links=links,
        )

        forwarder_list_response.additional_properties = d
        return forwarder_list_response

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
