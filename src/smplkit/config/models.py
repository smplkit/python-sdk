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

    Attributes:
        id: The config identifier (slug), or ``None`` for unsaved configs.
        name: Display name.
        description: Optional description.
        parent: Parent config id (slug), or ``None`` for root configs.
        items: Base values dict (``{key: raw_value}``), settable.
        items_raw: Full typed items (``{key: {value, type, description}}``).
        environments: Dict mapping environment names to their overrides.
        created_at: Creation timestamp.
        updated_at: Last-modified timestamp.
    """

    id: str | None
    name: str
    description: str | None
    parent: str | None
    environments: dict[str, Any]
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        client: ConfigClient,
        *,
        id: str | None = None,
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

    @items.setter
    def items(self, value: dict[str, Any]) -> None:
        """Set base items from a plain ``{key: raw_value}`` dict."""
        wrapped: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(v, dict) and "value" in v:
                wrapped[k] = v
            else:
                wrapped[k] = {"value": v}
        self._items_raw = wrapped

    @property
    def items_raw(self) -> dict[str, Any]:
        """Return the full typed items ``{key: {value, type, description}}``."""
        return dict(self._items_raw)

    def save(self) -> None:
        """Persist this config to the server.

        Creates a new config if unsaved, or updates the existing one.

        Raises:
            SmplNotFoundError: If the config no longer exists (update).
            SmplValidationError: If the server rejects the request.
        """
        if self.created_at is None:
            other = self._client._create_config(self)
        else:
            other = self._client._update_config_from_model(self)
        self._apply(other)

    def _apply(self, other: Config) -> None:
        """Copy all properties from *other* into this instance."""
        self.id = other.id
        self.name = other.name
        self.description = other.description
        self.parent = other.parent
        self._items_raw = other._items_raw
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def _build_chain(self, configs: list[Config] | None = None) -> list[dict[str, Any]]:
        """Walk the parent chain and return config data dicts child-to-root.

        Args:
            configs: Optional pre-fetched list of configs to look up parents
                by ID, avoiding extra network calls.
        """
        chain = [{"id": self.id, "items": self._items_raw, "environments": self.environments}]
        current = self
        configs_by_id = {c.id: c for c in configs} if configs else {}
        while current.parent is not None:
            parent_config = configs_by_id.get(current.parent)
            if parent_config is None:
                parent_config = self._client.get(current.parent)
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
        return f"Config(id={self.id!r}, name={self.name!r})"


class AsyncConfig:
    """Async variant of :class:`Config`.

    Attributes:
        id: The config identifier (slug), or ``None`` for unsaved configs.
        name: Display name.
        description: Optional description.
        parent: Parent config id (slug), or ``None`` for root configs.
        items: Base values dict (``{key: raw_value}``), settable.
        items_raw: Full typed items (``{key: {value, type, description}}``).
        environments: Dict mapping environment names to their overrides.
        created_at: Creation timestamp.
        updated_at: Last-modified timestamp.
    """

    id: str | None
    name: str
    description: str | None
    parent: str | None
    environments: dict[str, Any]
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        client: AsyncConfigClient,
        *,
        id: str | None = None,
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

    @items.setter
    def items(self, value: dict[str, Any]) -> None:
        """Set base items from a plain ``{key: raw_value}`` dict."""
        wrapped: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(v, dict) and "value" in v:
                wrapped[k] = v
            else:
                wrapped[k] = {"value": v}
        self._items_raw = wrapped

    @property
    def items_raw(self) -> dict[str, Any]:
        """Return the full typed items ``{key: {value, type, description}}``."""
        return dict(self._items_raw)

    async def save(self) -> None:
        """Persist this config to the server.

        Creates a new config if unsaved, or updates the existing one.

        Raises:
            SmplNotFoundError: If the config no longer exists (update).
            SmplValidationError: If the server rejects the request.
        """
        if self.created_at is None:
            other = await self._client._create_config(self)
        else:
            other = await self._client._update_config_from_model(self)
        self._apply(other)

    def _apply(self, other: AsyncConfig) -> None:
        """Copy all properties from *other* into this instance."""
        self.id = other.id
        self.name = other.name
        self.description = other.description
        self.parent = other.parent
        self._items_raw = other._items_raw
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    async def _build_chain(self, configs: list[AsyncConfig] | None = None) -> list[dict[str, Any]]:
        """Walk the parent chain and return config data dicts child-to-root.

        Args:
            configs: Optional pre-fetched list of configs to look up parents
                by ID, avoiding extra network calls.
        """
        chain = [{"id": self.id, "items": self._items_raw, "environments": self.environments}]
        current = self
        configs_by_id = {c.id: c for c in configs} if configs else {}
        while current.parent is not None:
            parent_config = configs_by_id.get(current.parent)
            if parent_config is None:
                parent_config = await self._client.get(current.parent)
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
        return f"AsyncConfig(id={self.id!r}, name={self.name!r})"
