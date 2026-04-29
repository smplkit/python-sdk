"""Stateless helpers shared between the runtime and management flag clients."""

from __future__ import annotations

from typing import Any

from smplkit._generated.flags.models.flag import Flag as GenFlag
from smplkit._generated.flags.models.flag_environment import FlagEnvironment as GenFlagEnvironment
from smplkit._generated.flags.models.flag_environments import FlagEnvironments as GenFlagEnvironments
from smplkit._generated.flags.models.flag_resource import FlagResource as ResourceFlag
from smplkit._generated.flags.models.flag_response import FlagResponse as ResponseFlag
from smplkit._generated.flags.models.flag_rule import FlagRule as GenFlagRule
from smplkit._generated.flags.models.flag_rule_logic import FlagRuleLogic as GenFlagRuleLogic
from smplkit._generated.flags.models.flag_value import FlagValue as GenFlagValue


def _extract_environments(environments: Any) -> dict[str, Any]:
    """Extract environments from a generated FlagEnvironments object to plain dicts."""
    from smplkit._generated.flags.types import UNSET

    if environments is None or isinstance(environments, type(UNSET)):
        return {}
    type_name = type(environments).__name__
    if type_name == "Unset":
        return {}
    if isinstance(environments, GenFlagEnvironments):
        result: dict[str, Any] = {}
        for env_name, env_obj in environments.additional_properties.items():
            entry: dict[str, Any] = {}
            if not isinstance(env_obj.enabled, type(UNSET)):
                entry["enabled"] = env_obj.enabled
            default_val = env_obj.default
            if not isinstance(default_val, type(UNSET)):
                entry["default"] = default_val
            rules_val = env_obj.rules
            if not isinstance(rules_val, type(UNSET)):
                entry["rules"] = [_extract_rule(r) for r in rules_val]
            else:
                entry["rules"] = []
            result[env_name] = entry
        return result
    if isinstance(environments, dict):
        return dict(environments)
    return {}


def _extract_rule(rule: Any) -> dict[str, Any]:
    """Extract a FlagRule to a plain dict."""
    from smplkit._generated.flags.types import UNSET

    result: dict[str, Any] = {
        "logic": dict(rule.logic.additional_properties) if hasattr(rule.logic, "additional_properties") else {},
        "value": rule.value,
    }
    if not isinstance(rule.description, type(UNSET)) and rule.description is not None:
        result["description"] = rule.description
    return result


def _extract_values(values: Any) -> list[dict[str, Any]] | None:
    """Extract a list of FlagValue to plain dicts, or None for unconstrained."""
    if values is None:
        return None
    if not values:
        return []
    result = []
    for v in values:
        entry: dict[str, Any] = {"name": v.name, "value": v.value}
        result.append(entry)
    return result


def _unset_to_none(value: Any) -> Any:
    """Convert Unset sentinels to None."""
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _build_gen_flag(
    *,
    name: str,
    type_: str,
    default: Any,
    values: list[dict[str, Any]] | None,
    description: str | None = None,
    environments: dict[str, Any] | None = None,
) -> GenFlag:
    """Build a generated Flag model from plain values."""
    gen_values: list[GenFlagValue] | None = None
    if values is not None:
        gen_values = [GenFlagValue(name=v["name"], value=v["value"]) for v in values]

    gen_envs: GenFlagEnvironments | Any
    if environments:
        gen_envs = GenFlagEnvironments()
        env_props: dict[str, GenFlagEnvironment] = {}
        for env_name, env_data in environments.items():
            rules = []
            for r in env_data.get("rules", []):
                logic_obj = GenFlagRuleLogic()
                logic_obj.additional_properties = dict(r.get("logic", {}))
                rule_obj = GenFlagRule(
                    logic=logic_obj,
                    value=r.get("value"),
                    description=r.get("description"),
                )
                rules.append(rule_obj)
            env_obj = GenFlagEnvironment(
                enabled=env_data.get("enabled", False),
                default=env_data.get("default"),
                rules=rules,
            )
            env_props[env_name] = env_obj
        gen_envs.additional_properties = env_props
    else:
        from smplkit._generated.flags.types import UNSET

        gen_envs = UNSET

    return GenFlag(
        name=name,
        type_=type_,
        default=default,
        values=gen_values,
        description=description,
        environments=gen_envs,
    )


def _build_flag_request_body(flag: Any, *, flag_id: str | None = None) -> ResponseFlag:
    """Wrap a Flag model's data in the JSON:API request envelope."""
    gen_flag = _build_gen_flag(
        name=flag.name,
        type_=flag.type,
        default=flag.default,
        values=flag.values,
        description=flag.description,
        environments=flag.environments or None,
    )
    resource = ResourceFlag(attributes=gen_flag, id=flag_id, type_="flag")
    return ResponseFlag(data=resource)


def _flag_dict_from_json(data: dict[str, Any]) -> dict[str, Any]:
    """Extract flat flag attributes from a JSON:API response ``data`` block."""
    attrs = data["attributes"]
    values_raw = attrs.get("values")
    values: list[dict[str, Any]] | None = None
    if values_raw is not None:
        values = [{"name": v["name"], "value": v["value"]} for v in values_raw]
    envs: dict[str, Any] = {}
    for env_key, env_data in (attrs.get("environments") or {}).items():
        envs[env_key] = {
            "enabled": env_data.get("enabled", False),
            "default": env_data.get("default"),
            "rules": env_data.get("rules", []),
        }
    return {
        "id": data.get("id", ""),
        "name": attrs["name"],
        "type": attrs["type"],
        "default": attrs["default"],
        "values": values,
        "description": attrs.get("description"),
        "environments": envs,
        "created_at": attrs.get("created_at"),
        "updated_at": attrs.get("updated_at"),
    }
