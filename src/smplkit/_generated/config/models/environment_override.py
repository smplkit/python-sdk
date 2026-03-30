from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import Union

if TYPE_CHECKING:
    from ..models.environment_override_values_type_0 import EnvironmentOverrideValuesType0


T = TypeVar("T", bound="EnvironmentOverride")


@_attrs_define
class EnvironmentOverride:
    """Schema for per-environment overrides.

    Attributes:
        values (Union['EnvironmentOverrideValuesType0', None, Unset]):
    """

    values: Union["EnvironmentOverrideValuesType0", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.environment_override_values_type_0 import EnvironmentOverrideValuesType0

        values: Union[None, Unset, dict[str, Any]]
        if isinstance(self.values, Unset):
            values = UNSET
        elif isinstance(self.values, EnvironmentOverrideValuesType0):
            values = self.values.to_dict()
        else:
            values = self.values

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if values is not UNSET:
            field_dict["values"] = values

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.environment_override_values_type_0 import EnvironmentOverrideValuesType0

        d = dict(src_dict)

        def _parse_values(data: object) -> Union["EnvironmentOverrideValuesType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                values_type_0 = EnvironmentOverrideValuesType0.from_dict(data)

                return values_type_0
            except:  # noqa: E722
                pass
            return cast(Union["EnvironmentOverrideValuesType0", None, Unset], data)

        values = _parse_values(d.pop("values", UNSET))

        environment_override = cls(
            values=values,
        )

        environment_override.additional_properties = d
        return environment_override

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
