"""Flag and ContextType resource models returned by the management API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from smplkit.flags.client import AsyncFlagsClient, FlagsClient


class Flag:
    """A flag resource (sync).  Returned by :class:`FlagsClient` methods."""

    def __init__(
        self,
        client: FlagsClient,
        *,
        id: str,
        key: str,
        name: str,
        type: str,
        default: Any,
        values: list[dict[str, Any]],
        description: str | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.key = key
        self.name = name
        self.type = type
        self.default = default
        self.values = values
        self.description = description
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def update(
        self,
        *,
        environments: dict[str, Any] | None = None,
        values: list[dict[str, Any]] | None = None,
        default: Any = None,
        description: str | None = None,
        name: str | None = None,
    ) -> None:
        """Update this flag (sync).  Only provided fields are changed."""
        updated = self._client._update_flag(
            flag=self,
            environments=environments,
            values=values,
            default=default,
            description=description,
            name=name,
        )
        self._apply(updated)

    def addRule(self, built_rule: dict[str, Any]) -> None:
        """Add a rule to a specific environment (sync)."""
        env_key = built_rule.get("environment")
        if env_key is None:
            raise ValueError(
                "Built rule must include 'environment' key. "
                "Use Rule(...).environment('env_key').when(...).serve(...).build()"
            )
        # Re-fetch current state to avoid stale data
        current = self._client.get(self.id)
        self._apply(current)

        envs = dict(self.environments)
        env_data = dict(envs.get(env_key, {"enabled": True, "rules": []}))
        rules = list(env_data.get("rules", []))

        rule_copy = {k: v for k, v in built_rule.items() if k != "environment"}
        rules.append(rule_copy)
        env_data["rules"] = rules
        envs[env_key] = env_data

        updated = self._client._update_flag(flag=self, environments=envs)
        self._apply(updated)

    def _apply(self, other: Flag) -> None:
        """Copy properties from *other* into this instance."""
        self.id = other.id
        self.key = other.key
        self.name = other.name
        self.type = other.type
        self.default = other.default
        self.values = other.values
        self.description = other.description
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"Flag(key={self.key!r}, type={self.type!r}, default={self.default!r})"


class AsyncFlag:
    """A flag resource (async).  Returned by :class:`AsyncFlagsClient` methods."""

    def __init__(
        self,
        client: AsyncFlagsClient,
        *,
        id: str,
        key: str,
        name: str,
        type: str,
        default: Any,
        values: list[dict[str, Any]],
        description: str | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.key = key
        self.name = name
        self.type = type
        self.default = default
        self.values = values
        self.description = description
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    async def update(
        self,
        *,
        environments: dict[str, Any] | None = None,
        values: list[dict[str, Any]] | None = None,
        default: Any = None,
        description: str | None = None,
        name: str | None = None,
    ) -> None:
        """Update this flag (async).  Only provided fields are changed."""
        updated = await self._client._update_flag(
            flag=self,
            environments=environments,
            values=values,
            default=default,
            description=description,
            name=name,
        )
        self._apply(updated)

    async def addRule(self, built_rule: dict[str, Any]) -> None:
        """Add a rule to a specific environment (async)."""
        env_key = built_rule.get("environment")
        if env_key is None:
            raise ValueError(
                "Built rule must include 'environment' key. "
                "Use Rule(...).environment('env_key').when(...).serve(...).build()"
            )
        # Re-fetch current state to avoid stale data
        current = await self._client.get(self.id)
        self._apply(current)

        envs = dict(self.environments)
        env_data = dict(envs.get(env_key, {"enabled": True, "rules": []}))
        rules = list(env_data.get("rules", []))

        rule_copy = {k: v for k, v in built_rule.items() if k != "environment"}
        rules.append(rule_copy)
        env_data["rules"] = rules
        envs[env_key] = env_data

        updated = await self._client._update_flag(flag=self, environments=envs)
        self._apply(updated)

    def _apply(self, other: AsyncFlag) -> None:
        """Copy properties from *other* into this instance."""
        self.id = other.id
        self.key = other.key
        self.name = other.name
        self.type = other.type
        self.default = other.default
        self.values = other.values
        self.description = other.description
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"AsyncFlag(key={self.key!r}, type={self.type!r}, default={self.default!r})"


class ContextType:
    """A context type resource returned by management API methods."""

    def __init__(
        self,
        *,
        id: str,
        key: str,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.key = key
        self.name = name
        self.attributes = attributes or {}

    def __repr__(self) -> str:
        return f"ContextType(key={self.key!r}, name={self.name!r})"
