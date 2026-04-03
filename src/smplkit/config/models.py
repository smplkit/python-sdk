"""Config and AsyncConfig — rich model objects for a single configuration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from smplkit.config.client import AsyncConfigClient, ConfigClient

logger = logging.getLogger("smplkit")


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
        items: Base values dict (``{key: raw_value}``).
        items_raw: Full typed items (``{key: {value, type, description}}``).
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
        items: dict[str, Any] | None = None,
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
        self._items_raw = items or {}
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def items(self) -> dict[str, Any]:
        """Return base values as a plain dict ``{key: raw_value}``.

        Extracts ``.value`` from each item definition for backward
        compatibility with runtime resolution.
        """
        return {k: v["value"] if isinstance(v, dict) and "value" in v else v for k, v in self._items_raw.items()}

    @property
    def items_raw(self) -> dict[str, Any]:
        """Return the full typed items ``{key: {value, type, description}}``."""
        return dict(self._items_raw)

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        items: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> None:
        """Update this config's attributes on the server.

        Builds the request from current attribute values, overriding with
        any provided kwargs. Updates local attributes in place on success.

        Args:
            name: New display name.
            description: New description.
            items: New items in typed shape (replaces entirely).
            environments: New environments dict (replaces entirely).

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        new_name = name if name is not None else self.name
        new_desc = description if description is not None else self.description
        new_items = items if items is not None else self._items_raw
        new_envs = environments if environments is not None else self.environments

        updated = self._client._update_config(
            config_id=self.id,
            name=new_name,
            key=self.key,
            description=new_desc,
            parent=self.parent,
            items=new_items,
            environments=new_envs,
        )
        self.name = updated.name
        self.description = updated.description
        self._items_raw = updated._items_raw
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    def set_items(
        self,
        items: dict[str, Any],
        *,
        environment: str | None = None,
    ) -> None:
        """Replace base or environment-specific items and PUT the config.

        Args:
            items: The items dict to set.  For base items, use the typed shape
                ``{key: {value, type, description}}``.  For environment
                overrides, use ``{key: raw_value}``.
            environment: If provided, replaces that environment's values.
                If ``None``, replaces the base ``items``.

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        if environment is None:
            new_items = items
            new_envs = self.environments
        else:
            new_items = self._items_raw
            env_entry = dict(self.environments.get(environment, {}))
            env_entry["values"] = items
            new_envs = {**self.environments, environment: env_entry}

        updated = self._client._update_config(
            config_id=self.id,
            name=self.name,
            key=self.key,
            description=self.description,
            parent=self.parent,
            items=new_items,
            environments=new_envs,
        )
        self._items_raw = updated._items_raw
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    # Keep backward-compatible alias
    set_values = set_items

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
            merged = {**self._items_raw, key: {"value": value}}
            self.set_items(merged)
        else:
            existing = dict((self.environments.get(environment, {}) or {}).get("values", {}) or {})
            existing[key] = value
            self.set_items(existing, environment=environment)

    def _build_chain(self) -> list[dict[str, Any]]:
        """Walk the parent chain and return config data dicts child-to-root."""
        chain = [{"id": self.id, "items": self._items_raw, "environments": self.environments}]
        current = self
        while current.parent is not None:
            parent_config = self._client.get(id=current.parent)
            chain.append(
                {
                    "id": parent_config.id,
                    "items": parent_config._items_raw,
                    "environments": parent_config.environments,
                }
            )
            current = parent_config
        return chain

    def __repr__(self) -> str:
        return f"Config(id={self.id!r}, key={self.key!r}, name={self.name!r})"


class AsyncConfig:
    """Async variant of :class:`Config`.

    All management-plane methods are ``async``.

    Attributes:
        id: Unique identifier (UUID).
        key: Human-readable key (e.g. ``"user_service"``).
        name: Display name.
        description: Optional description.
        parent: Parent config UUID, or ``None`` for root configs.
        items: Base values dict (``{key: raw_value}``).
        items_raw: Full typed items (``{key: {value, type, description}}``).
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
        items: dict[str, Any] | None = None,
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
        self._items_raw = items or {}
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def items(self) -> dict[str, Any]:
        """Return base values as a plain dict ``{key: raw_value}``."""
        return {k: v["value"] if isinstance(v, dict) and "value" in v else v for k, v in self._items_raw.items()}

    @property
    def items_raw(self) -> dict[str, Any]:
        """Return the full typed items ``{key: {value, type, description}}``."""
        return dict(self._items_raw)

    async def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        items: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> None:
        """Update this config's attributes on the server.

        Args:
            name: New display name.
            description: New description.
            items: New items in typed shape (replaces entirely).
            environments: New environments dict (replaces entirely).

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        new_name = name if name is not None else self.name
        new_desc = description if description is not None else self.description
        new_items = items if items is not None else self._items_raw
        new_envs = environments if environments is not None else self.environments

        updated = await self._client._update_config(
            config_id=self.id,
            name=new_name,
            key=self.key,
            description=new_desc,
            parent=self.parent,
            items=new_items,
            environments=new_envs,
        )
        self.name = updated.name
        self.description = updated.description
        self._items_raw = updated._items_raw
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    async def set_items(
        self,
        items: dict[str, Any],
        *,
        environment: str | None = None,
    ) -> None:
        """Replace base or environment-specific items and PUT the config.

        Args:
            items: The items dict to set.
            environment: If provided, replaces that environment's values.
                If ``None``, replaces the base ``items``.

        Raises:
            SmplNotFoundError: If the config no longer exists.
            SmplValidationError: If the server rejects the request.
        """
        if environment is None:
            new_items = items
            new_envs = self.environments
        else:
            new_items = self._items_raw
            env_entry = dict(self.environments.get(environment, {}))
            env_entry["values"] = items
            new_envs = {**self.environments, environment: env_entry}

        updated = await self._client._update_config(
            config_id=self.id,
            name=self.name,
            key=self.key,
            description=self.description,
            parent=self.parent,
            items=new_items,
            environments=new_envs,
        )
        self._items_raw = updated._items_raw
        self.environments = updated.environments
        self.updated_at = updated.updated_at

    # Keep backward-compatible alias
    set_values = set_items

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
            merged = {**self._items_raw, key: {"value": value}}
            await self.set_items(merged)
        else:
            existing = dict((self.environments.get(environment, {}) or {}).get("values", {}) or {})
            existing[key] = value
            await self.set_items(existing, environment=environment)

    async def _build_chain(self) -> list[dict[str, Any]]:
        """Walk the parent chain and return config data dicts child-to-root."""
        chain = [{"id": self.id, "items": self._items_raw, "environments": self.environments}]
        current = self
        while current.parent is not None:
            parent_config = await self._client.get(id=current.parent)
            chain.append(
                {
                    "id": parent_config.id,
                    "items": parent_config._items_raw,
                    "environments": parent_config.environments,
                }
            )
            current = parent_config
        return chain

    def __repr__(self) -> str:
        return f"AsyncConfig(id={self.id!r}, key={self.key!r}, name={self.name!r})"
