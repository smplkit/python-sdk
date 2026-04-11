from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import Union

if TYPE_CHECKING:
    from ..models.product_plans import ProductPlans
    from ..models.product_limits import ProductLimits


T = TypeVar("T", bound="Product")


@_attrs_define
class Product:
    """
    Attributes:
        display_name (str):
        description (str):
        limits (ProductLimits):
        plans (ProductPlans):
        coming_soon (Union[Unset, bool]):  Default: False.
    """

    display_name: str
    description: str
    limits: "ProductLimits"
    plans: "ProductPlans"
    coming_soon: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        display_name = self.display_name

        description = self.description

        limits = self.limits.to_dict()

        plans = self.plans.to_dict()

        coming_soon = self.coming_soon

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "display_name": display_name,
                "description": description,
                "limits": limits,
                "plans": plans,
            }
        )
        if coming_soon is not UNSET:
            field_dict["coming_soon"] = coming_soon

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.product_plans import ProductPlans
        from ..models.product_limits import ProductLimits

        d = dict(src_dict)
        display_name = d.pop("display_name")

        description = d.pop("description")

        limits = ProductLimits.from_dict(d.pop("limits"))

        plans = ProductPlans.from_dict(d.pop("plans"))

        coming_soon = d.pop("coming_soon", UNSET)

        product = cls(
            display_name=display_name,
            description=description,
            limits=limits,
            plans=plans,
            coming_soon=coming_soon,
        )

        product.additional_properties = d
        return product

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
