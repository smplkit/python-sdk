"""Deep-merge resolution algorithm for config inheritance chains.

Implements the resolution logic from ADR-024 sections 2.5 and 2.6.
"""

from __future__ import annotations

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dicts, with *override* taking precedence.

    Args:
        base: The base dictionary (lower priority).
        override: The override dictionary (higher priority).

    Returns:
        A new dict with values from both, where *override* wins on conflict.
        Nested dicts are merged recursively. Non-dict values (strings,
        numbers, booleans, arrays, null) are replaced wholesale.
    """
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve(chain: list[dict[str, Any]], environment: str) -> dict[str, Any]:
    """Resolve the full configuration for an environment given a config chain.

    Walks the chain from root (last element) to child (first element),
    accumulating values via deep merge so that child configs override
    parent configs.

    For each config in the chain, the config's base ``values`` are first
    merged with its environment-specific values (environment wins), then
    that result is merged on top of the accumulated parent result (child
    wins over parent).

    Args:
        chain: Ordered list of config data dicts from child (index 0) to
            root ancestor (last index). Each dict has ``values`` (dict) and
            ``environments`` (dict).
        environment: The environment key to resolve for.

    Returns:
        A flat dict of config item keys to their resolved JSON values.
    """
    accumulated: dict[str, Any] = {}

    # Walk from root to child (reverse order)
    for config_data in reversed(chain):
        base_values = dict(config_data.get("values") or {})
        env_data = (config_data.get("environments") or {}).get(environment, {})
        env_values = dict(env_data.get("values") or {}) if isinstance(env_data, dict) else {}

        # Merge environment overrides on top of base values
        config_resolved = deep_merge(base_values, env_values)

        # Merge this config's resolved values on top of accumulated parent values
        accumulated = deep_merge(accumulated, config_resolved)

    return accumulated
