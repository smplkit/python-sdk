"""Config and AsyncConfig — rich model objects for a single configuration."""

from __future__ import annotations

import datetime
import logging
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any

from smplkit.config.runtime import ConfigRuntime

if TYPE_CHECKING:
    from smplkit.config.client import AsyncConfigClient, ConfigClient

logger = logging.getLogger("smplkit")


class _AsyncConnectResult:
    """Wrapper that makes ``AsyncConfig.connect()`` usable as both
    ``await config.connect(...)`` and ``async with config.connect(...) as rt:``.
    """

    def __init__(self, coro: Coroutine[Any, Any, ConfigRuntime]) -> None:
        self._coro = coro
        self._runtime: ConfigRuntime | None = None

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self) -> ConfigRuntime:
        self._runtime = await self._coro
        return self._runtime

    async def __aexit__(self, *args: Any) -> None:
        if self._runtime is not None:
            await self._runtime.close()


class Config:
    """A configuration resource fetched from the Smpl Config service.

    Instances are returned by :class:`ConfigClient` methods and provide
    management-plane operations (update, set values) as well as the
    :meth:`connect` entry point for runtime value resolution.

    Attributes:
        id: Unique identifier (UUID).
        key: Human-readable key (e.g. ``"user_service"``).
        name: Display name.
        description: Optional description.
        parent: Parent config UUID, or ``None`` for root configs.
        values: Base values dict.
        environments: Dict mapping environment names to their overrides.
        created_at: Creation timestamp.
        updated_at: Last-modified timestamp.
    """

    def __init__(
        self,
        client: ConfigClient,
        *,
        id: str,
        key: str,
        name: str,
        description: str | None = None,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self._client = client
        self.id = id
        self.key = key
        self.name = name
        self.description = description
        self.parent = parent
        self.values = values or {}
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        values: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> None:
        """Update this config's attributes on the server.

        Builds the request from current attribute values, overriding with
        any provided kwargs. Updates local attributes in place on success.

        Args:
            name: New display name.
            description: New description.
            values: New base values (replaces entirely).
            environments: New environments dict (replaces entirely).

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        new_name = name if name is not None else self.name
        new_desc = description if description is not None else self.description
        new_values = values if values is not None else self.values
        new_envs = environments if environments is not None else self.environments

        updated = self._client._update_config(
            config_id=self.id,
            name=new_name,
            key=self.key,
            description=new_desc,
            parent=self.parent,
            values=new_values,
            environments=new_envs,
        )
        self.name = updated.name
        self.description = updated.description
        self.values = updated.values
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    def set_values(
        self,
        values: dict[str, Any],
        *,
        environment: str | None = None,
    ) -> None:
        """Replace base or environment-specific values and PUT the config.

        Args:
            values: The values dict to set.
            environment: If provided, replaces that environment's values.
                If ``None``, replaces the base ``values``.

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        if environment is None:
            new_values = values
            new_envs = self.environments
        else:
            new_values = self.values
            env_entry = dict(self.environments.get(environment, {}))
            env_entry["values"] = values
            new_envs = {**self.environments, environment: env_entry}

        updated = self._client._update_config(
            config_id=self.id,
            name=self.name,
            key=self.key,
            description=self.description,
            parent=self.parent,
            values=new_values,
            environments=new_envs,
        )
        self.values = updated.values
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    def set_value(
        self,
        key: str,
        value: Any,
        *,
        environment: str | None = None,
    ) -> None:
        """Set a single key within base or environment-specific values.

        Merges the key into existing values rather than replacing all values.

        Args:
            key: The config key to set.
            value: The value to assign.
            environment: Target environment, or ``None`` for base values.

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        if environment is None:
            merged = {**self.values, key: value}
            self.set_values(merged)
        else:
            existing = dict(
                (self.environments.get(environment, {}) or {}).get("values", {}) or {}
            )
            existing[key] = value
            self.set_values(existing, environment=environment)

    def connect(self, environment: str, *, timeout: float = 30) -> ConfigRuntime:
        """Connect to this config for runtime value resolution.

        Eagerly fetches this config and its full parent chain, resolves
        values for the given environment via deep merge, and returns a
        :class:`ConfigRuntime` with a fully populated local cache.

        A background WebSocket connection is started for real-time updates.
        If the WebSocket fails to connect, the runtime operates in
        cache-only mode.

        Args:
            environment: The environment to resolve for (e.g.
                ``"production"``).
            timeout: Maximum seconds to wait for the initial fetch.

        Returns:
            A :class:`ConfigRuntime` ready for synchronous value reads.

        Raises:
            SmplTimeoutError: If the fetch exceeds *timeout*.
            SmplConnectionError: If a network request fails.
        """
        chain = self._build_chain()
        api_key = self._client._parent._api_key
        base_url = self._client._parent._http_client._base_url

        def _fetch_chain() -> list[dict[str, Any]]:
            return self._build_chain()

        return ConfigRuntime(
            config_key=self.key,
            config_id=self.id,
            environment=environment,
            chain=chain,
            api_key=api_key,
            base_url=base_url,
            fetch_chain_fn=_fetch_chain,
        )

    def _build_chain(self) -> list[dict[str, Any]]:
        """Walk the parent chain and return config data dicts child-to-root."""
        chain = [{"id": self.id, "values": self.values, "environments": self.environments}]
        current = self
        while current.parent is not None:
            parent_config = self._client.get(id=current.parent)
            chain.append({
                "id": parent_config.id,
                "values": parent_config.values,
                "environments": parent_config.environments,
            })
            current = parent_config
        return chain

    def __repr__(self) -> str:
        return f"Config(id={self.id!r}, key={self.key!r}, name={self.name!r})"


class AsyncConfig:
    """Async variant of :class:`Config`.

    All management-plane methods are ``async``. The :meth:`connect` method
    returns a :class:`ConfigRuntime` whose value-access methods are always
    synchronous.

    Attributes:
        id: Unique identifier (UUID).
        key: Human-readable key (e.g. ``"user_service"``).
        name: Display name.
        description: Optional description.
        parent: Parent config UUID, or ``None`` for root configs.
        values: Base values dict.
        environments: Dict mapping environment names to their overrides.
        created_at: Creation timestamp.
        updated_at: Last-modified timestamp.
    """

    def __init__(
        self,
        client: AsyncConfigClient,
        *,
        id: str,
        key: str,
        name: str,
        description: str | None = None,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self._client = client
        self.id = id
        self.key = key
        self.name = name
        self.description = description
        self.parent = parent
        self.values = values or {}
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    async def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        values: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> None:
        """Update this config's attributes on the server.

        Args:
            name: New display name.
            description: New description.
            values: New base values (replaces entirely).
            environments: New environments dict (replaces entirely).

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        new_name = name if name is not None else self.name
        new_desc = description if description is not None else self.description
        new_values = values if values is not None else self.values
        new_envs = environments if environments is not None else self.environments

        updated = await self._client._update_config(
            config_id=self.id,
            name=new_name,
            key=self.key,
            description=new_desc,
            parent=self.parent,
            values=new_values,
            environments=new_envs,
        )
        self.name = updated.name
        self.description = updated.description
        self.values = updated.values
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    async def set_values(
        self,
        values: dict[str, Any],
        *,
        environment: str | None = None,
    ) -> None:
        """Replace base or environment-specific values and PUT the config.

        Args:
            values: The values dict to set.
            environment: If provided, replaces that environment's values.
                If ``None``, replaces the base ``values``.

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        if environment is None:
            new_values = values
            new_envs = self.environments
        else:
            new_values = self.values
            env_entry = dict(self.environments.get(environment, {}))
            env_entry["values"] = values
            new_envs = {**self.environments, environment: env_entry}

        updated = await self._client._update_config(
            config_id=self.id,
            name=self.name,
            key=self.key,
            description=self.description,
            parent=self.parent,
            values=new_values,
            environments=new_envs,
        )
        self.values = updated.values
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    async def set_value(
        self,
        key: str,
        value: Any,
        *,
        environment: str | None = None,
    ) -> None:
        """Set a single key within base or environment-specific values.

        Args:
            key: The config key to set.
            value: The value to assign.
            environment: Target environment, or ``None`` for base values.

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        if environment is None:
            merged = {**self.values, key: value}
            await self.set_values(merged)
        else:
            existing = dict(
                (self.environments.get(environment, {}) or {}).get("values", {}) or {}
            )
            existing[key] = value
            await self.set_values(existing, environment=environment)

    def connect(self, environment: str, *, timeout: float = 30) -> _AsyncConnectResult:
        """Connect to this config for runtime value resolution.

        Eagerly fetches this config and its full parent chain, resolves
        values for the given environment via deep merge, and returns a
        :class:`ConfigRuntime` with a fully populated local cache.

        A background WebSocket connection is started for real-time updates.
        If the WebSocket fails to connect, the runtime operates in
        cache-only mode.

        Supports both ``await`` and ``async with``::

            runtime = await config.connect("production")
            async with config.connect("production") as runtime:
                ...

        Args:
            environment: The environment to resolve for (e.g.
                ``"production"``).
            timeout: Maximum seconds to wait for the initial fetch.

        Returns:
            A :class:`ConfigRuntime` ready for synchronous value reads.

        Raises:
            SmplTimeoutError: If the fetch exceeds *timeout*.
            SmplConnectionError: If a network request fails.
        """
        async def _connect() -> ConfigRuntime:
            chain = await self._build_chain()
            api_key = self._client._parent._api_key
            base_url = self._client._parent._http_client._base_url

            def _fetch_chain():
                return self._build_chain()

            return ConfigRuntime(
                config_key=self.key,
                config_id=self.id,
                environment=environment,
                chain=chain,
                api_key=api_key,
                base_url=base_url,
                fetch_chain_fn=_fetch_chain,
            )

        return _AsyncConnectResult(_connect())

    async def _build_chain(self) -> list[dict[str, Any]]:
        """Walk the parent chain and return config data dicts child-to-root."""
        chain = [{"id": self.id, "values": self.values, "environments": self.environments}]
        current = self
        while current.parent is not None:
            parent_config = await self._client.get(id=current.parent)
            chain.append({
                "id": parent_config.id,
                "values": parent_config.values,
                "environments": parent_config.environments,
            })
            current = parent_config
        return chain

    def __repr__(self) -> str:
        return f"AsyncConfig(id={self.id!r}, key={self.key!r}, name={self.name!r})"
