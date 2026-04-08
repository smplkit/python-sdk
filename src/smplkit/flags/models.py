"""Unified flag model hierarchy — management + runtime in a single class tree."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from smplkit.flags.client import AsyncFlagsClient, FlagsClient


class Flag:
    """A flag resource (sync).

    Serves as both a management model (save, addRule, convenience methods)
    and a runtime handle (.get() for evaluation).

    Subclasses (BooleanFlag, StringFlag, NumberFlag, JsonFlag) override
    .get() to return a typed value.
    """

    def __init__(
        self,
        client: FlagsClient,
        *,
        id: str | None = None,
        key: str,
        name: str,
        type: str,
        default: Any,
        values: list[dict[str, Any]] | None = None,
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
        self.values = values or []
        self.description = description
        self.environments = environments if environments is not None else {}
        self.created_at = created_at
        self.updated_at = updated_at

    # ------------------------------------------------------------------
    # Management: save (create or update)
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist this flag to the server.

        POST if ``id is None`` (create), PUT if ``id`` is set (update).
        Applies the server response back to this instance.
        """
        if self.id is None:
            created = self._client._create_flag(self)
            self._apply(created)
        else:
            updated = self._client._update_flag(flag=self)
            self._apply(updated)

    # ------------------------------------------------------------------
    # Management: local mutations
    # ------------------------------------------------------------------

    def addRule(self, built_rule: dict[str, Any]) -> Flag:
        """Append a rule to a specific environment (local mutation, no HTTP).

        The *built_rule* dict must include an ``"environment"`` key.  The
        rule (without the ``environment`` key) is appended to that
        environment's rules list.  Call :meth:`save` to persist.

        Returns *self* for chaining.
        """
        env_key = built_rule.get("environment")
        if env_key is None:
            raise ValueError(
                "Built rule must include 'environment' key. "
                "Use Rule(...).environment('env_key').when(...).serve(...).build()"
            )
        rule_copy = {k: v for k, v in built_rule.items() if k != "environment"}
        env_data = self.environments.setdefault(env_key, {})
        env_data.setdefault("rules", []).append(rule_copy)
        return self

    def setEnvironmentEnabled(self, env_key: str, enabled: bool) -> None:
        """Set whether the flag is enabled in *env_key* (local mutation)."""
        self.environments.setdefault(env_key, {})["enabled"] = enabled

    def setEnvironmentDefault(self, env_key: str, default: Any) -> None:
        """Set the environment-specific default (local mutation)."""
        self.environments.setdefault(env_key, {})["default"] = default

    def clearRules(self, env_key: str) -> None:
        """Remove all rules from *env_key* (local mutation)."""
        self.environments.setdefault(env_key, {})["rules"] = []

    # ------------------------------------------------------------------
    # Runtime: evaluation
    # ------------------------------------------------------------------

    def get(self, context: list | None = None) -> Any:
        """Evaluate this flag and return its current value.

        Evaluation is local (no I/O).  On the first call, the client
        lazily initializes its flag store and WebSocket connection.
        """
        return self._client._evaluate_handle(self.key, self.default, context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

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


class BooleanFlag(Flag):
    """A boolean flag — .get() returns bool."""

    def get(self, context: list | None = None) -> bool:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, bool):
            return value
        return self.default


class StringFlag(Flag):
    """A string flag — .get() returns str."""

    def get(self, context: list | None = None) -> str:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, str):
            return value
        return self.default


class NumberFlag(Flag):
    """A numeric flag — .get() returns int | float."""

    def get(self, context: list | None = None) -> int | float:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        return self.default


class JsonFlag(Flag):
    """A JSON flag — .get() returns dict."""

    def get(self, context: list | None = None) -> dict[str, Any]:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, dict):
            return value
        return self.default


# ===================================================================
# Async variants
# ===================================================================


class AsyncFlag:
    """A flag resource (async).

    Same interface as :class:`Flag` but :meth:`save` is async.
    Local mutations (addRule, setEnvironmentEnabled, etc.) and
    evaluation (.get()) are synchronous.
    """

    def __init__(
        self,
        client: AsyncFlagsClient,
        *,
        id: str | None = None,
        key: str,
        name: str,
        type: str,
        default: Any,
        values: list[dict[str, Any]] | None = None,
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
        self.values = values or []
        self.description = description
        self.environments = environments if environments is not None else {}
        self.created_at = created_at
        self.updated_at = updated_at

    # ------------------------------------------------------------------
    # Management: save (create or update)
    # ------------------------------------------------------------------

    async def save(self) -> None:
        """Persist this flag to the server (async).

        POST if ``id is None`` (create), PUT if ``id`` is set (update).
        """
        if self.id is None:
            created = await self._client._create_flag(self)
            self._apply(created)
        else:
            updated = await self._client._update_flag(flag=self)
            self._apply(updated)

    # ------------------------------------------------------------------
    # Management: local mutations (sync)
    # ------------------------------------------------------------------

    def addRule(self, built_rule: dict[str, Any]) -> AsyncFlag:
        env_key = built_rule.get("environment")
        if env_key is None:
            raise ValueError(
                "Built rule must include 'environment' key. "
                "Use Rule(...).environment('env_key').when(...).serve(...).build()"
            )
        rule_copy = {k: v for k, v in built_rule.items() if k != "environment"}
        env_data = self.environments.setdefault(env_key, {})
        env_data.setdefault("rules", []).append(rule_copy)
        return self

    def setEnvironmentEnabled(self, env_key: str, enabled: bool) -> None:
        self.environments.setdefault(env_key, {})["enabled"] = enabled

    def setEnvironmentDefault(self, env_key: str, default: Any) -> None:
        self.environments.setdefault(env_key, {})["default"] = default

    def clearRules(self, env_key: str) -> None:
        self.environments.setdefault(env_key, {})["rules"] = []

    # ------------------------------------------------------------------
    # Runtime: evaluation (sync — evaluation is local, no I/O)
    # ------------------------------------------------------------------

    def get(self, context: list | None = None) -> Any:
        return self._client._evaluate_handle(self.key, self.default, context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply(self, other: AsyncFlag) -> None:
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


class AsyncBooleanFlag(AsyncFlag):
    def get(self, context: list | None = None) -> bool:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, bool):
            return value
        return self.default


class AsyncStringFlag(AsyncFlag):
    def get(self, context: list | None = None) -> str:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, str):
            return value
        return self.default


class AsyncNumberFlag(AsyncFlag):
    def get(self, context: list | None = None) -> int | float:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        return self.default


class AsyncJsonFlag(AsyncFlag):
    def get(self, context: list | None = None) -> dict[str, Any]:
        value = self._client._evaluate_handle(self.key, self.default, context)
        if isinstance(value, dict):
            return value
        return self.default
