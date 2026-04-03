"""Level resolution algorithm per ADR-034 §3.1."""

from __future__ import annotations

from typing import Any

_FALLBACK_LEVEL = "INFO"


def resolve_level(
    logger_key: str,
    environment: str,
    loggers: dict[str, dict[str, Any]],
    groups: dict[str, dict[str, Any]],
) -> str:
    """Resolve the effective log level for a logger in an environment.

    Resolution chain (first non-null wins):

    1. Logger's own ``environments[env].level``
    2. Logger's own ``level``
    3. Group chain (recursive: group's env level -> group's level -> parent group...)
    4. Dot-notation ancestry (walk ``com.acme.payments`` -> ``com.acme`` -> ``com``,
       applying steps 1-3 at each)
    5. System fallback: ``"INFO"``

    Args:
        logger_key: The normalized logger key.
        environment: The current environment name.
        loggers: Dict of all loggers keyed by ``key``.
        groups: Dict of all log groups keyed by ``id``.

    Returns:
        The resolved smplkit level string.
    """
    result = _resolve_for_entry(logger_key, environment, loggers, groups)
    if result is not None:
        return result

    # Dot-notation ancestry: walk up the hierarchy
    parts = logger_key.split(".")
    for i in range(len(parts) - 1, 0, -1):
        ancestor_key = ".".join(parts[:i])
        result = _resolve_for_entry(ancestor_key, environment, loggers, groups)
        if result is not None:
            return result

    return _FALLBACK_LEVEL


def _resolve_for_entry(
    key: str,
    environment: str,
    loggers: dict[str, dict[str, Any]],
    groups: dict[str, dict[str, Any]],
) -> str | None:
    """Try to resolve a level for a single entry (logger or ancestor)."""
    entry = loggers.get(key)
    if entry is None:
        return None

    # Step 1: env override on the entry itself
    env_level = _env_level(entry, environment)
    if env_level is not None:
        return env_level

    # Step 2: base level on the entry itself
    base = entry.get("level")
    if base is not None:
        return base

    # Step 3: group chain
    group_id = entry.get("group")
    return _resolve_group_chain(group_id, environment, groups)


def _resolve_group_chain(
    group_id: str | None,
    environment: str,
    groups: dict[str, dict[str, Any]],
) -> str | None:
    """Walk the group chain looking for a level."""
    visited: set[str] = set()
    current_id = group_id
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        group = groups.get(current_id)
        if group is None:
            break
        env_level = _env_level(group, environment)
        if env_level is not None:
            return env_level
        base = group.get("level")
        if base is not None:
            return base
        current_id = group.get("group")
    return None


def _env_level(entry: dict[str, Any], environment: str) -> str | None:
    """Extract the environment-specific level from an entry, if present."""
    envs = entry.get("environments")
    if envs and isinstance(envs, dict):
        env_data = envs.get(environment)
        if env_data and isinstance(env_data, dict):
            level = env_data.get("level")
            if level is not None:
                return level
    return None
