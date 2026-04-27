from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast


T = TypeVar("T", bound="AccountWipeResponse")


@_attrs_define
class AccountWipeResponse:
    """Summary of resources removed by a wipe.

    Example:
        {'api_keys_deleted': 1, 'configs_deleted': 9, 'context_types_deleted': 3, 'contexts_deleted': 30, 'failures':
            [], 'flags_deleted': 14, 'log_groups_deleted': 3, 'loggers_deleted': 10}

    Attributes:
        configs_deleted (int | Unset):  Default: 0.
        flags_deleted (int | Unset):  Default: 0.
        loggers_deleted (int | Unset):  Default: 0.
        log_groups_deleted (int | Unset):  Default: 0.
        contexts_deleted (int | Unset):  Default: 0.
        context_types_deleted (int | Unset):  Default: 0.
        api_keys_deleted (int | Unset):  Default: 0.
        failures (list[str] | Unset):
    """

    configs_deleted: int | Unset = 0
    flags_deleted: int | Unset = 0
    loggers_deleted: int | Unset = 0
    log_groups_deleted: int | Unset = 0
    contexts_deleted: int | Unset = 0
    context_types_deleted: int | Unset = 0
    api_keys_deleted: int | Unset = 0
    failures: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        configs_deleted = self.configs_deleted

        flags_deleted = self.flags_deleted

        loggers_deleted = self.loggers_deleted

        log_groups_deleted = self.log_groups_deleted

        contexts_deleted = self.contexts_deleted

        context_types_deleted = self.context_types_deleted

        api_keys_deleted = self.api_keys_deleted

        failures: list[str] | Unset = UNSET
        if not isinstance(self.failures, Unset):
            failures = self.failures

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if configs_deleted is not UNSET:
            field_dict["configs_deleted"] = configs_deleted
        if flags_deleted is not UNSET:
            field_dict["flags_deleted"] = flags_deleted
        if loggers_deleted is not UNSET:
            field_dict["loggers_deleted"] = loggers_deleted
        if log_groups_deleted is not UNSET:
            field_dict["log_groups_deleted"] = log_groups_deleted
        if contexts_deleted is not UNSET:
            field_dict["contexts_deleted"] = contexts_deleted
        if context_types_deleted is not UNSET:
            field_dict["context_types_deleted"] = context_types_deleted
        if api_keys_deleted is not UNSET:
            field_dict["api_keys_deleted"] = api_keys_deleted
        if failures is not UNSET:
            field_dict["failures"] = failures

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        configs_deleted = d.pop("configs_deleted", UNSET)

        flags_deleted = d.pop("flags_deleted", UNSET)

        loggers_deleted = d.pop("loggers_deleted", UNSET)

        log_groups_deleted = d.pop("log_groups_deleted", UNSET)

        contexts_deleted = d.pop("contexts_deleted", UNSET)

        context_types_deleted = d.pop("context_types_deleted", UNSET)

        api_keys_deleted = d.pop("api_keys_deleted", UNSET)

        failures = cast(list[str], d.pop("failures", UNSET))

        account_wipe_response = cls(
            configs_deleted=configs_deleted,
            flags_deleted=flags_deleted,
            loggers_deleted=loggers_deleted,
            log_groups_deleted=log_groups_deleted,
            contexts_deleted=contexts_deleted,
            context_types_deleted=context_types_deleted,
            api_keys_deleted=api_keys_deleted,
            failures=failures,
        )

        account_wipe_response.additional_properties = d
        return account_wipe_response

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
