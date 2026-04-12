from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.catalog_bundle_resource_type import CatalogBundleResourceType
from ..models.catalog_bundle_resource_type import check_catalog_bundle_resource_type
from typing import cast

if TYPE_CHECKING:
    from ..models.catalog_bundle_attributes import CatalogBundleAttributes


T = TypeVar("T", bound="CatalogBundleResource")


@_attrs_define
class CatalogBundleResource:
    """
    Example:
        {'attributes': {'display_name': 'Standard Bundle', 'plan': 'standard', 'price_monthly_cents': 14900, 'products':
            ['config', 'flags', 'logging']}, 'id': 'standard', 'type': 'bundle'}

    Attributes:
        type_ (CatalogBundleResourceType):
        attributes (CatalogBundleAttributes):
        id (None | str | Unset):
    """

    type_: CatalogBundleResourceType
    attributes: CatalogBundleAttributes
    id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_: str = self.type_

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
        from ..models.catalog_bundle_attributes import CatalogBundleAttributes

        d = dict(src_dict)
        type_ = check_catalog_bundle_resource_type(d.pop("type"))

        attributes = CatalogBundleAttributes.from_dict(d.pop("attributes"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        catalog_bundle_resource = cls(
            type_=type_,
            attributes=attributes,
            id=id,
        )

        catalog_bundle_resource.additional_properties = d
        return catalog_bundle_resource

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
