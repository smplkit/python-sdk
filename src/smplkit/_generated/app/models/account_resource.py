from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import Union
from typing import Literal

if TYPE_CHECKING:
    from ..models.account import Account


T = TypeVar("T", bound="AccountResource")


@_attrs_define
class AccountResource:
    """
    Example:
        {'attributes': {'created_at': '2026-03-20T11:02:16.616Z', 'has_stripe_customer': False, 'key': 'acme_corp',
            'name': 'Acme Corp'}, 'id': 'd290f1ee-6c54-4b01-90e6-d701748f0851', 'type': 'account'}

    Attributes:
        type_ (Literal['account']):
        attributes (Account):  Example: {'created_at': '2026-03-20T11:02:16.616Z', 'has_stripe_customer': False, 'key':
            'acme_corp', 'name': 'Acme Corp'}.
        id (Union[None, Unset, str]):
    """

    type_: Literal["account"]
    attributes: "Account"
    id: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        attributes = self.attributes.to_dict()

        id: Union[None, Unset, str]
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
        from ..models.account import Account

        d = dict(src_dict)
        type_ = cast(Literal["account"], d.pop("type"))
        if type_ != "account":
            raise ValueError(f"type must match const 'account', got '{type_}'")

        attributes = Account.from_dict(d.pop("attributes"))

        def _parse_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        id = _parse_id(d.pop("id", UNSET))

        account_resource = cls(
            type_=type_,
            attributes=attributes,
            id=id,
        )

        account_resource.additional_properties = d
        return account_resource

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
