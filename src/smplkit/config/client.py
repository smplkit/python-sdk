"""ConfigClient and AsyncConfigClient — management and prescriptive operations for configs."""

from __future__ import annotations


import logging
import threading
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from uuid import UUID

from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplNotConnectedError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit._resolver import resolve
from smplkit._generated.config.api.configs import (
    create_config,
    delete_config,
    get_config,
    list_configs,
    update_config,
)
from smplkit._generated.config.models.config import Config as GenConfig
from smplkit._generated.config.models.config_environments_type_0 import (
    ConfigEnvironmentsType0,
)
from smplkit._generated.config.models.config_items_type_0 import ConfigItemsType0
from smplkit._generated.config.models.resource_config import ResourceConfig
from smplkit._generated.config.models.response_config import ResponseConfig
from smplkit.config.models import AsyncConfig, Config

if TYPE_CHECKING:
    from smplkit.client import AsyncSmplClient, SmplClient

logger = logging.getLogger("smplkit")


def _make_items(items: dict[str, Any] | None) -> ConfigItemsType0 | None:
    """Convert a plain items dict to the generated ConfigItemsType0 model.

    Accepts items in the typed shape ``{key: {value, type, description}}``.
    Plain ``{key: raw_value}`` dicts are auto-wrapped for convenience.
    """
    if items is None:
        return None
    from smplkit._generated.config.models.config_item_definition import (
        ConfigItemDefinition,
    )

    obj = ConfigItemsType0()
    wrapped: dict[str, ConfigItemDefinition] = {}
    for k, v in items.items():
        if isinstance(v, dict) and "value" in v:
            wrapped[k] = ConfigItemDefinition(
                value=v["value"],
                type_=v.get("type"),
                description=v.get("description"),
            )
        else:
            wrapped[k] = ConfigItemDefinition(value=v)
    obj.additional_properties = wrapped
    return obj


def _make_environments(
    environments: dict[str, Any] | None,
) -> ConfigEnvironmentsType0 | None:
    """Convert a plain dict to the generated ConfigEnvironmentsType0 model.

    Environment override values are wrapped as ``{key: {value: raw}}``.
    """
    if environments is None:
        return None
    from smplkit._generated.config.models.config_item_override import (
        ConfigItemOverride,
    )
    from smplkit._generated.config.models.environment_override import (
        EnvironmentOverride,
    )
    from smplkit._generated.config.models.environment_override_values_type_0 import (
        EnvironmentOverrideValuesType0,
    )

    obj = ConfigEnvironmentsType0()
    env_props: dict[str, EnvironmentOverride] = {}
    for env_name, env_data in environments.items():
        if isinstance(env_data, dict):
            raw_values = env_data.get("values") or {}
            vals_obj = EnvironmentOverrideValuesType0()
            wrapped_vals: dict[str, ConfigItemOverride] = {}
            for k, v in raw_values.items():
                if isinstance(v, dict) and "value" in v:
                    wrapped_vals[k] = ConfigItemOverride(value=v["value"])
                else:
                    wrapped_vals[k] = ConfigItemOverride(value=v)
            vals_obj.additional_properties = wrapped_vals
            env_props[env_name] = EnvironmentOverride(values=vals_obj)
        else:
            env_props[env_name] = EnvironmentOverride()
    obj.additional_properties = env_props
    return obj


def _extract_items(items: Any) -> dict[str, Any]:
    """Extract a typed items dict from a generated items object.

    Returns ``{key: {value, type, description}}`` (the full typed shape).
    """
    if items is None or isinstance(items, type(None)):
        return {}
    type_name = type(items).__name__
    if type_name == "Unset":
        return {}
    if isinstance(items, ConfigItemsType0):
        result: dict[str, Any] = {}
        for k, item_def in items.additional_properties.items():
            entry: dict[str, Any] = {"value": item_def.value}
            type_val = getattr(item_def, "type_", None)
            if type_val is not None and type(type_val).__name__ != "Unset":
                entry["type"] = type_val.value if hasattr(type_val, "value") else str(type_val)
            desc_val = getattr(item_def, "description", None)
            if desc_val is not None and type(desc_val).__name__ != "Unset":
                entry["description"] = desc_val
            result[k] = entry
        return result
    if isinstance(items, dict):
        return dict(items)
    return {}


def _extract_environments(environments: Any) -> dict[str, Any]:
    """Extract a plain dict from a generated environments object.

    Environment override values are unwrapped from ``{key: {value: raw}}``
    back to ``{key: raw}`` for the SDK model layer.
    """
    if environments is None or isinstance(environments, type(None)):
        return {}
    type_name = type(environments).__name__
    if type_name == "Unset":
        return {}
    if isinstance(environments, ConfigEnvironmentsType0):
        result: dict[str, Any] = {}
        for env_name, env_override in environments.additional_properties.items():
            env_entry: dict[str, Any] = {}
            if hasattr(env_override, "values") and env_override.values is not None:
                vals_type = type(env_override.values).__name__
                if vals_type != "Unset":
                    raw_vals: dict[str, Any] = {}
                    if hasattr(env_override.values, "additional_properties"):
                        for k, item_override in env_override.values.additional_properties.items():
                            if hasattr(item_override, "value"):
                                raw_vals[k] = item_override.value
                            else:
                                raw_vals[k] = item_override
                    env_entry["values"] = raw_vals
            result[env_name] = env_entry
        return result
    if isinstance(environments, dict):
        return dict(environments)
    return {}


def _extract_datetime(value: Any) -> Any:
    """Pass through datetime objects, return None for Unset/None."""
    if value is None:
        return None
    # Check for Unset sentinel
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _unset_to_none(value: Any) -> Any:
    """Convert Unset sentinels to None."""
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _check_response_status(status_code: HTTPStatus, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions.

    Args:
        status_code: The HTTP status code from the response.
        content: The raw response body for error messages.

    Raises:
        SmplNotFoundError: On 404.
        SmplConflictError: On 409.
        SmplValidationError: On 422.
    """
    code = int(status_code)
    if code == 404:
        raise SmplNotFoundError(content.decode("utf-8", errors="replace"))
    if code == 409:
        raise SmplConflictError(content.decode("utf-8", errors="replace"))
    if code == 422:
        raise SmplValidationError(content.decode("utf-8", errors="replace"))


def _build_request_body(
    *,
    name: str,
    key: str | None = None,
    description: str | None = None,
    parent: str | None = None,
    items: dict[str, Any] | None = None,
    environments: dict[str, Any] | None = None,
) -> ResponseConfig:
    """Build a JSON:API request body for create/update operations."""
    attrs = GenConfig(
        name=name,
        key=key,
        description=description,
        parent=parent,
        items=_make_items(items),
        environments=_make_environments(environments),
    )
    resource = ResourceConfig(attributes=attrs, type_="config")
    return ResponseConfig(data=resource)


class ConfigChangeEvent:
    """Describes a single config value change.

    Attributes:
        config_key: The config key that changed.
        item_key: The item key within the config that changed.
        old_value: The previous value.
        new_value: The updated value.
        source: How the change was delivered (``"websocket"`` or ``"manual"``).
    """

    def __init__(
        self,
        *,
        config_key: str,
        item_key: str,
        old_value: Any,
        new_value: Any,
        source: str,
    ) -> None:
        self.config_key = config_key
        self.item_key = item_key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source

    def __repr__(self) -> str:
        return (
            f"ConfigChangeEvent(config_key={self.config_key!r}, item_key={self.item_key!r}, "
            f"old_value={self.old_value!r}, new_value={self.new_value!r}, source={self.source!r})"
        )


class ConfigClient:
    """Synchronous management and prescriptive client for Smpl Config.

    Provides CRUD operations on config resources and prescriptive
    value access after ``client.connect()``.  Obtained via
    ``SmplClient(...).config``.

    Raises:
        SmplConnectionError: If a network request fails.
        SmplTimeoutError: If an operation exceeds its timeout.
    """

    def __init__(self, parent: SmplClient) -> None:
        self._parent = parent
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []

    def _connect_internal(self) -> None:
        """Fetch all configs, resolve values for the environment, and cache.

        Called by :meth:`SmplClient.connect`.
        """
        configs = self.list()
        environment = self._parent._environment
        cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = cfg._build_chain()
            cache[cfg.key] = resolve(chain, environment)
        with self._cache_lock:
            self._config_cache = cache
        self._connected = True

    def get(self, *args: str, key: str | None = None, id: str | None = None, default: Any = None) -> Any:
        """Fetch a config by key/UUID (management) or read a resolved value (prescriptive).

        **Prescriptive mode** (positional args)::

            value = client.config.get("db_connection", "host")
            all_values = client.config.get("db_connection")

        Requires :meth:`SmplClient.connect` to have been called.

        **Management mode** (keyword args)::

            cfg = client.config.get(key="db_connection")
            cfg = client.config.get(id="some-uuid")

        Works without ``connect()``.

        Args:
            *args: Positional args for prescriptive access:
                ``(config_key,)`` or ``(config_key, item_key)``.
            key: The human-readable config key for management access.
            id: The config UUID for management access.
            default: Default value for prescriptive access when key is missing.

        Returns:
            In prescriptive mode: the resolved value, a dict of all values,
            or *default*.
            In management mode: the matching :class:`Config`.

        Raises:
            SmplNotConnectedError: If prescriptive mode is used before connect.
            ValueError: If management args are ambiguous.
            SmplNotFoundError: If no matching config exists (management mode).
        """
        if args:
            # Prescriptive mode: get("db_connection", "host")
            if not self._connected:
                raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")
            config_key = args[0]
            item_key = args[1] if len(args) > 1 else None
            resolved = self._config_cache.get(config_key)
            if resolved is None:
                return default
            if item_key is None:
                return dict(resolved)
            return resolved.get(item_key, default)

        # Management mode
        if (key is None) == (id is None):
            raise ValueError("Exactly one of 'key' or 'id' must be provided.")

        try:
            if id is not None:
                return self._get_by_id(id)
            return self._get_by_key(key)  # type: ignore[arg-type]
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise

    def get_str(self, config_key: str, item_key: str, *, default: str | None = None) -> str | None:
        """Return a config value if it is a string, else *default*.

        Requires :meth:`SmplClient.connect`.
        """
        value = self.get(config_key, item_key)
        return value if isinstance(value, str) else default

    def get_int(self, config_key: str, item_key: str, *, default: int | None = None) -> int | None:
        """Return a config value if it is an int, else *default*.

        Bools are excluded (``isinstance(True, int)`` is ``True`` in Python).
        Requires :meth:`SmplClient.connect`.
        """
        value = self.get(config_key, item_key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def get_bool(self, config_key: str, item_key: str, *, default: bool | None = None) -> bool | None:
        """Return a config value if it is a bool, else *default*.

        Requires :meth:`SmplClient.connect`.
        """
        value = self.get(config_key, item_key)
        return value if isinstance(value, bool) else default

    def get_float(self, config_key: str, item_key: str, *, default: float | None = None) -> float | None:
        """Return a config value if it is a float or int, else *default*.

        Bools are excluded. Ints are promoted to float.
        Requires :meth:`SmplClient.connect`.
        """
        value = self.get(config_key, item_key)
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        return default

    def refresh(self) -> None:
        """Re-fetch all configs, re-resolve for the environment, and update the cache.

        Fires change listeners for any values that differ from the previous cache.

        Requires :meth:`SmplClient.connect` to have been called at least once.

        Raises:
            SmplNotConnectedError: If called before connect.
            SmplConnectionError: If the HTTP fetch fails.
        """
        if not self._connected:
            raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")
        configs = self.list()
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = cfg._build_chain()
            new_cache[cfg.key] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
        self._fire_change_listeners(old_cache, new_cache, source="manual")

    def on_change(
        self,
        callback: Callable[[ConfigChangeEvent], None],
        *,
        config_key: str | None = None,
        item_key: str | None = None,
    ) -> None:
        """Register a listener that fires when a config value changes.

        Args:
            callback: Called with a :class:`ConfigChangeEvent` on change.
            config_key: If provided, only fire for changes to this config.
            item_key: If provided, only fire for changes to this item key.
        """
        self._listeners.append((callback, config_key, item_key))

    def _fire_change_listeners(
        self,
        old_cache: dict[str, dict[str, Any]],
        new_cache: dict[str, dict[str, Any]],
        *,
        source: str,
    ) -> None:
        """Diff two caches and fire listeners for any changed values."""
        all_config_keys = set(old_cache.keys()) | set(new_cache.keys())
        for cfg_key in all_config_keys:
            old_items = old_cache.get(cfg_key, {})
            new_items = new_cache.get(cfg_key, {})
            all_item_keys = set(old_items.keys()) | set(new_items.keys())
            for i_key in all_item_keys:
                old_val = old_items.get(i_key)
                new_val = new_items.get(i_key)
                if old_val == new_val:
                    continue
                event = ConfigChangeEvent(
                    config_key=cfg_key,
                    item_key=i_key,
                    old_value=old_val,
                    new_value=new_val,
                    source=source,
                )
                for callback, ck_filter, ik_filter in self._listeners:
                    if ck_filter is not None and ck_filter != cfg_key:
                        continue
                    if ik_filter is not None and ik_filter != i_key:
                        continue
                    try:
                        callback(event)
                    except Exception:
                        logger.error(
                            "Exception in on_change listener for %s.%s",
                            cfg_key,
                            i_key,
                            exc_info=True,
                        )

    def _get_by_id(self, config_id: str) -> Config:
        """Fetch a config by UUID."""
        response = get_config.sync_detailed(
            UUID(config_id),
            client=self._parent._http_client,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Config {config_id} not found")
        return self._to_model(response.parsed)

    def _get_by_key(self, key: str) -> Config:
        """Fetch a config by key using the list endpoint with a filter."""
        response = list_configs.sync_detailed(
            client=self._parent._http_client,
            filterkey=key,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        items = response.parsed.data
        if not items:
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        return self._resource_to_model(items[0])

    def create(
        self,
        *,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        items: dict[str, Any] | None = None,
    ) -> Config:
        """Create a new config.

        Args:
            name: Display name for the config.
            key: Human-readable key. Auto-generated if omitted.
            description: Optional description.
            parent: Parent config UUID. Defaults to the account's common
                config if omitted.
            items: Initial items in typed shape ``{key: {value, type, desc}}``.

        Returns:
            The created :class:`Config`.

        Raises:
            SmplValidationError: If the server rejects the request.
        """
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            items=items,
        )
        try:
            response = create_config.sync_detailed(
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to create config")
        return self._to_model(response.parsed)

    def list(self) -> list[Config]:
        """List all configs for the account.

        Returns:
            A list of :class:`Config` objects.
        """
        try:
            response = list_configs.sync_detailed(
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._resource_to_model(r) for r in response.parsed.data]

    def delete(self, config_id: str) -> None:
        """Delete a config by UUID.

        Args:
            config_id: The UUID of the config to delete.

        Raises:
            SmplNotFoundError: If the config does not exist.
            SmplConflictError: If the config has children.
        """
        try:
            response = delete_config.sync_detailed(
                UUID(config_id),
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    def _update_config(
        self,
        *,
        config_id: str,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        items: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> Config:
        """Internal: PUT a full config update and return the updated model."""
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            items=items,
            environments=environments,
        )
        try:
            response = update_config.sync_detailed(
                UUID(config_id),
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to update config")
        return self._to_model(response.parsed)

    def _to_model(self, parsed: Any) -> Config:
        """Convert a ConfigResponse (single resource) to a Config model."""
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> Config:
        """Convert a ConfigResource to a Config model."""
        attrs = resource.attributes
        return Config(
            self,
            id=_unset_to_none(resource.id) or "",
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            description=_unset_to_none(attrs.description),
            parent=_unset_to_none(attrs.parent),
            items=_extract_items(attrs.items),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


class AsyncConfigClient:
    """Asynchronous management and prescriptive client for Smpl Config.

    Provides CRUD operations on config resources and prescriptive
    value access after ``client.connect()``.  Obtained via
    ``AsyncSmplClient(...).config``.

    Raises:
        SmplConnectionError: If a network request fails.
        SmplTimeoutError: If an operation exceeds its timeout.
    """

    def __init__(self, parent: AsyncSmplClient) -> None:
        self._parent = parent
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []

    async def _connect_internal(self) -> None:
        """Fetch all configs, resolve values for the environment, and cache.

        Called by :meth:`AsyncSmplClient.connect`.
        """
        configs = await self.list()
        environment = self._parent._environment
        cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = await cfg._build_chain()
            cache[cfg.key] = resolve(chain, environment)
        with self._cache_lock:
            self._config_cache = cache
        self._connected = True

    async def get(self, *args: str, key: str | None = None, id: str | None = None, default: Any = None) -> Any:
        """Fetch a config by key/UUID (management) or read a resolved value (prescriptive).

        **Prescriptive mode** (positional args)::

            value = await client.config.get("db_connection", "host")

        Requires :meth:`AsyncSmplClient.connect` to have been called.

        **Management mode** (keyword args)::

            cfg = await client.config.get(key="db_connection")

        Works without ``connect()``.
        """
        if args:
            # Prescriptive mode: get("db_connection", "host")
            if not self._connected:
                raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")
            config_key = args[0]
            item_key = args[1] if len(args) > 1 else None
            resolved = self._config_cache.get(config_key)
            if resolved is None:
                return default
            if item_key is None:
                return dict(resolved)
            return resolved.get(item_key, default)

        # Management mode
        if (key is None) == (id is None):
            raise ValueError("Exactly one of 'key' or 'id' must be provided.")

        try:
            if id is not None:
                return await self._get_by_id(id)
            return await self._get_by_key(key)  # type: ignore[arg-type]
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise

    async def get_str(self, config_key: str, item_key: str, *, default: str | None = None) -> str | None:
        """Return a config value if it is a string, else *default*.

        Requires :meth:`AsyncSmplClient.connect`.
        """
        value = await self.get(config_key, item_key)
        return value if isinstance(value, str) else default

    async def get_int(self, config_key: str, item_key: str, *, default: int | None = None) -> int | None:
        """Return a config value if it is an int, else *default*.

        Bools are excluded. Requires :meth:`AsyncSmplClient.connect`.
        """
        value = await self.get(config_key, item_key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    async def get_bool(self, config_key: str, item_key: str, *, default: bool | None = None) -> bool | None:
        """Return a config value if it is a bool, else *default*.

        Requires :meth:`AsyncSmplClient.connect`.
        """
        value = await self.get(config_key, item_key)
        return value if isinstance(value, bool) else default

    async def get_float(self, config_key: str, item_key: str, *, default: float | None = None) -> float | None:
        """Return a config value if it is a float or int, else *default*.

        Bools are excluded. Ints are promoted to float.
        Requires :meth:`AsyncSmplClient.connect`.
        """
        value = await self.get(config_key, item_key)
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        return default

    async def refresh(self) -> None:
        """Re-fetch all configs, re-resolve for the environment, and update the cache.

        Fires change listeners for any values that differ from the previous cache.

        Requires :meth:`AsyncSmplClient.connect`.

        Raises:
            SmplNotConnectedError: If called before connect.
            SmplConnectionError: If the HTTP fetch fails.
        """
        if not self._connected:
            raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")
        configs = await self.list()
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = await cfg._build_chain()
            new_cache[cfg.key] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
        self._fire_change_listeners(old_cache, new_cache, source="manual")

    def on_change(
        self,
        callback: Callable[[ConfigChangeEvent], None],
        *,
        config_key: str | None = None,
        item_key: str | None = None,
    ) -> None:
        """Register a listener that fires when a config value changes.

        Args:
            callback: Called with a :class:`ConfigChangeEvent` on change.
            config_key: If provided, only fire for changes to this config.
            item_key: If provided, only fire for changes to this item key.
        """
        self._listeners.append((callback, config_key, item_key))

    def _fire_change_listeners(
        self,
        old_cache: dict[str, dict[str, Any]],
        new_cache: dict[str, dict[str, Any]],
        *,
        source: str,
    ) -> None:
        """Diff two caches and fire listeners for any changed values."""
        all_config_keys = set(old_cache.keys()) | set(new_cache.keys())
        for cfg_key in all_config_keys:
            old_items = old_cache.get(cfg_key, {})
            new_items = new_cache.get(cfg_key, {})
            all_item_keys = set(old_items.keys()) | set(new_items.keys())
            for i_key in all_item_keys:
                old_val = old_items.get(i_key)
                new_val = new_items.get(i_key)
                if old_val == new_val:
                    continue
                event = ConfigChangeEvent(
                    config_key=cfg_key,
                    item_key=i_key,
                    old_value=old_val,
                    new_value=new_val,
                    source=source,
                )
                for callback, ck_filter, ik_filter in self._listeners:
                    if ck_filter is not None and ck_filter != cfg_key:
                        continue
                    if ik_filter is not None and ik_filter != i_key:
                        continue
                    try:
                        callback(event)
                    except Exception:
                        logger.error(
                            "Exception in on_change listener for %s.%s",
                            cfg_key,
                            i_key,
                            exc_info=True,
                        )

    async def _get_by_id(self, config_id: str) -> AsyncConfig:
        """Fetch a config by UUID."""
        response = await get_config.asyncio_detailed(
            UUID(config_id),
            client=self._parent._http_client,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Config {config_id} not found")
        return self._to_model(response.parsed)

    async def _get_by_key(self, key: str) -> AsyncConfig:
        """Fetch a config by key using the list endpoint with a filter."""
        response = await list_configs.asyncio_detailed(
            client=self._parent._http_client,
            filterkey=key,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        items = response.parsed.data
        if not items:
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        return self._resource_to_model(items[0])

    async def create(
        self,
        *,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        items: dict[str, Any] | None = None,
    ) -> AsyncConfig:
        """Create a new config.

        Args:
            name: Display name for the config.
            key: Human-readable key. Auto-generated if omitted.
            description: Optional description.
            parent: Parent config UUID. Defaults to the account's common
                config if omitted.
            items: Initial items in typed shape ``{key: {value, type, desc}}``.

        Returns:
            The created :class:`AsyncConfig`.

        Raises:
            SmplValidationError: If the server rejects the request.
        """
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            items=items,
        )
        try:
            response = await create_config.asyncio_detailed(
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to create config")
        return self._to_model(response.parsed)

    async def list(self) -> list[AsyncConfig]:
        """List all configs for the account.

        Returns:
            A list of :class:`AsyncConfig` objects.
        """
        try:
            response = await list_configs.asyncio_detailed(
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._resource_to_model(r) for r in response.parsed.data]

    async def delete(self, config_id: str) -> None:
        """Delete a config by UUID.

        Args:
            config_id: The UUID of the config to delete.

        Raises:
            SmplNotFoundError: If the config does not exist.
            SmplConflictError: If the config has children.
        """
        try:
            response = await delete_config.asyncio_detailed(
                UUID(config_id),
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    async def _update_config(
        self,
        *,
        config_id: str,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        items: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> AsyncConfig:
        """Internal: PUT a full config update and return the updated model."""
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            items=items,
            environments=environments,
        )
        try:
            response = await update_config.asyncio_detailed(
                UUID(config_id),
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to update config")
        return self._to_model(response.parsed)

    def _to_model(self, parsed: Any) -> AsyncConfig:
        """Convert a ConfigResponse (single resource) to an AsyncConfig model."""
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> AsyncConfig:
        """Convert a ConfigResource to an AsyncConfig model."""
        attrs = resource.attributes
        return AsyncConfig(
            self,
            id=_unset_to_none(resource.id) or "",
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            description=_unset_to_none(attrs.description),
            parent=_unset_to_none(attrs.parent),
            items=_extract_items(attrs.items),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


def _maybe_reraise_network_error(exc: Exception) -> None:
    """Re-raise httpx exceptions as SDK exceptions if applicable."""
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        raise SmplTimeoutError(str(exc)) from exc
    if isinstance(exc, httpx.HTTPError):
        raise SmplConnectionError(str(exc)) from exc
    if isinstance(exc, (SmplNotFoundError, SmplConflictError, SmplValidationError)):
        raise exc
