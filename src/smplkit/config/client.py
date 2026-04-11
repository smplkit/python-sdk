"""ConfigClient and AsyncConfigClient — management and runtime operations for configs."""

from __future__ import annotations


import logging
import threading
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
    _raise_for_status,
)
from smplkit._helpers import key_to_display_name
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
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


def _build_request_body(
    *,
    config_id: str | None = None,
    name: str,
    description: str | None = None,
    parent: str | None = None,
    items: dict[str, Any] | None = None,
    environments: dict[str, Any] | None = None,
) -> ResponseConfig:
    """Build a JSON:API request body for create/update operations."""
    attrs = GenConfig(
        name=name,
        description=description,
        parent=parent,
        items=_make_items(items),
        environments=_make_environments(environments),
    )
    resource = ResourceConfig(attributes=attrs, id=config_id, type_="config")
    return ResponseConfig(data=resource)


def _unflatten(flat: dict[str, Any]) -> dict[str, Any]:
    """Convert dot-notation keys to a nested dict.

    ``{"database.host": "localhost", "database.port": 5432}``
    becomes ``{"database": {"host": "localhost", "port": 5432}}``.
    """
    nested: dict[str, Any] = {}
    for key, value in flat.items():
        parts = key.split(".")
        current = nested
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return nested


class ConfigChangeEvent:
    """Describes a single config value change.

    Attributes:
        config_id: The config id that changed.
        item_key: The item key within the config that changed.
        old_value: The previous value.
        new_value: The updated value.
        source: How the change was delivered (``"websocket"`` or ``"manual"``).
    """

    config_id: str
    item_key: str
    old_value: Any
    new_value: Any
    source: str

    def __init__(
        self,
        *,
        config_id: str,
        item_key: str,
        old_value: Any,
        new_value: Any,
        source: str,
    ) -> None:
        self.config_id = config_id
        self.item_key = item_key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source

    def __repr__(self) -> str:
        return (
            f"ConfigChangeEvent(config_id={self.config_id!r}, item_key={self.item_key!r}, "
            f"old_value={self.old_value!r}, new_value={self.new_value!r}, source={self.source!r})"
        )


class LiveConfigProxy:
    """A live proxy that always reflects the latest resolved config values.

    Returned by :meth:`ConfigClient.subscribe` and
    :meth:`AsyncConfigClient.subscribe`.

    Attribute access returns the current resolved value for the given
    item key. If a *model* was provided, the model is reconstructed
    from the latest values on each access.

    Supports both ``proxy.attr`` and ``proxy["key"]`` access styles.
    """

    def __init__(
        self,
        client: ConfigClient | AsyncConfigClient,
        config_id: str,
        model: type | None = None,
    ) -> None:
        object.__setattr__(self, "_client", client)
        object.__setattr__(self, "_config_id", config_id)
        object.__setattr__(self, "_model", model)

    def _current_values(self) -> dict[str, Any]:
        """Read the current resolved values from the client cache."""
        client = object.__getattribute__(self, "_client")
        config_id = object.__getattribute__(self, "_config_id")
        return dict(client._config_cache.get(config_id, {}))

    def _build_model(self) -> Any:
        """Build a model instance from current values, if a model was given."""
        model = object.__getattribute__(self, "_model")
        values = self._current_values()
        if model is None:
            return values
        nested = _unflatten(values)
        if hasattr(model, "model_validate"):
            return model.model_validate(nested)
        return model(**nested)

    def __getattr__(self, name: str) -> Any:
        model = object.__getattribute__(self, "_model")
        if model is not None:
            instance = self._build_model()
            return getattr(instance, name)
        values = self._current_values()
        try:
            return values[name]
        except KeyError:
            raise AttributeError(f"No config item {name!r}") from None

    def __getitem__(self, key: str) -> Any:
        values = self._current_values()
        return values[key]

    def __repr__(self) -> str:
        config_id = object.__getattribute__(self, "_config_id")
        model = object.__getattribute__(self, "_model")
        if model is not None:
            return f"LiveConfigProxy(config_id={config_id!r}, model={model.__name__})"
        return f"LiveConfigProxy(config_id={config_id!r})"


class ConfigClient:
    """Synchronous client for Smpl Config.

    Obtained via ``SmplClient(...).config``.
    """

    def __init__(self, parent: SmplClient) -> None:
        self._parent = parent
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []

    def _connect_internal(self) -> None:
        """Fetch all configs, resolve values for the environment, and cache.

        Idempotent — returns immediately if already connected.
        """
        if self._connected:
            return
        configs = self.list()
        environment = self._parent._environment
        cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = cfg._build_chain(configs)
            cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            self._config_cache = cache
        self._connected = True

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def new(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        parent: str | None = None,
    ) -> Config:
        """Return a new unsaved :class:`Config`.

        Call :meth:`Config.save` to persist it.

        Args:
            id: Config identifier (slug).
            name: Display name. Auto-generated from *id* if omitted.
            description: Optional description.
            parent: Parent config id (slug), or ``None``.

        Returns:
            A new :class:`Config` that has not yet been saved.
        """
        return Config(
            self,
            id=id,
            name=name or key_to_display_name(id),
            description=description,
            parent=parent,
        )

    def get(self, id: str) -> Config:
        """Fetch a config by id.

        Args:
            id: The config identifier (slug).

        Returns:
            The matching :class:`Config`.

        Raises:
            SmplNotFoundError: If no matching config exists.
        """
        try:
            response = get_config.sync_detailed(
                id,
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            raise SmplNotFoundError(f"Config with id '{id}' not found", status_code=404)
        return self._resource_to_model(response.parsed.data)

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

    def delete(self, id: str) -> None:
        """Delete a config by id.

        Args:
            id: The config identifier (slug).

        Raises:
            SmplNotFoundError: If the config does not exist.
            SmplConflictError: If the config has children.
        """
        try:
            response = delete_config.sync_detailed(
                id,
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    # ------------------------------------------------------------------
    # Runtime: resolve / subscribe
    # ------------------------------------------------------------------

    def resolve(self, id: str, model: type | None = None) -> Any:
        """Return resolved config values for *id*.

        If *model* is ``None``, returns a flat ``dict[str, Any]`` of
        resolved values.

        If *model* is provided, dot-notation keys (e.g. ``"database.host"``)
        are expanded into nested structures and the model is constructed.
        Supports Pydantic models, dataclasses, or any class accepting
        keyword arguments.

        Args:
            id: The config id to resolve.
            model: Optional model class to construct from resolved values.

        Returns:
            A flat dict, or an instance of *model*.
        """
        self._connect_internal()
        values = dict(self._config_cache.get(id, {}))
        metrics = self._parent._metrics
        if metrics is not None:
            metrics.record("config.resolutions", unit="resolutions", dimensions={"config": id})
        if model is None:
            return values
        nested = _unflatten(values)
        if hasattr(model, "model_validate"):
            return model.model_validate(nested)
        return model(**nested)

    def subscribe(self, id: str, model: type | None = None) -> LiveConfigProxy:
        """Return a :class:`LiveConfigProxy` for *id*.

        Values update automatically after :meth:`refresh`.

        Args:
            id: The config id to subscribe to.
            model: Optional model class — if provided, attribute access
                returns a model instance built from the latest values.

        Returns:
            A :class:`LiveConfigProxy`.
        """
        self._connect_internal()
        return LiveConfigProxy(self, id, model)

    # ------------------------------------------------------------------
    # Runtime: refresh / change listeners
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Re-fetch all configs and update resolved values.

        Fires change listeners for any values that differ from the previous state.

        Raises:
            SmplConnectionError: If the fetch fails.
        """
        configs = self.list()
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = cfg._build_chain(configs)
            new_cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
        self._fire_change_listeners(old_cache, new_cache, source="manual")

    def on_change(
        self, fn_or_id: Callable[[ConfigChangeEvent], None] | str | None = None, *, item_key: str | None = None
    ) -> Any:
        """Register a change listener.

        Supports three forms:

        - ``@client.config.on_change`` — global listener (bare decorator).
        - ``@client.config.on_change("id")`` — config-scoped listener.
        - ``@client.config.on_change("id", item_key="field")`` — item-scoped.
        """
        if callable(fn_or_id):
            # @on_change (bare decorator)
            self._listeners.append((fn_or_id, None, None))
            return fn_or_id
        elif isinstance(fn_or_id, str):
            # @on_change("id") or @on_change("id", item_key="field")
            config_id = fn_or_id

            def decorator(fn: Callable[[ConfigChangeEvent], None]) -> Callable[[ConfigChangeEvent], None]:
                self._listeners.append((fn, config_id, item_key))
                return fn

            return decorator
        else:
            # @on_change() — called with parens but no args

            def decorator(fn: Callable[[ConfigChangeEvent], None]) -> Callable[[ConfigChangeEvent], None]:
                self._listeners.append((fn, None, None))
                return fn

            return decorator

    def _fire_change_listeners(
        self,
        old_cache: dict[str, dict[str, Any]],
        new_cache: dict[str, dict[str, Any]],
        *,
        source: str,
    ) -> None:
        """Diff two caches and fire listeners for any changed values."""
        all_config_ids = set(old_cache.keys()) | set(new_cache.keys())
        for cfg_id in all_config_ids:
            old_items = old_cache.get(cfg_id, {})
            new_items = new_cache.get(cfg_id, {})
            all_item_keys = set(old_items.keys()) | set(new_items.keys())
            for i_key in all_item_keys:
                old_val = old_items.get(i_key)
                new_val = new_items.get(i_key)
                if old_val == new_val:
                    continue
                metrics = self._parent._metrics
                if metrics is not None:
                    metrics.record("config.changes", unit="changes", dimensions={"config": cfg_id})
                event = ConfigChangeEvent(
                    config_id=cfg_id,
                    item_key=i_key,
                    old_value=old_val,
                    new_value=new_val,
                    source=source,
                )
                for callback, ck_filter, ik_filter in self._listeners:
                    if ck_filter is not None and ck_filter != cfg_id:
                        continue
                    if ik_filter is not None and ik_filter != i_key:
                        continue
                    try:
                        callback(event)
                    except Exception:
                        logger.error(
                            "Exception in on_change listener for %s.%s",
                            cfg_id,
                            i_key,
                            exc_info=True,
                        )

    # ------------------------------------------------------------------
    # Internal: create / update for Config.save()
    # ------------------------------------------------------------------

    def _create_config(self, config: Config) -> Config:
        """Internal: POST a new config from a Config model (for Config.save)."""
        body = _build_request_body(
            config_id=config.id,
            name=config.name,
            description=config.description,
            parent=config.parent,
            items=config._items_raw,
            environments=config.environments,
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
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._to_model(response.parsed)

    def _update_config_from_model(self, config: Config) -> Config:
        """Internal: PUT a config update from a Config model (for Config.save)."""
        body = _build_request_body(
            config_id=config.id,
            name=config.name,
            description=config.description,
            parent=config.parent,
            items=config._items_raw,
            environments=config.environments,
        )
        try:
            response = update_config.sync_detailed(
                config.id,
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._to_model(response.parsed)

    # ------------------------------------------------------------------
    # Internal: model conversion
    # ------------------------------------------------------------------

    def _to_model(self, parsed: Any) -> Config:
        """Convert a ConfigResponse (single resource) to a Config model."""
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> Config:
        """Convert a ConfigResource to a Config model."""
        attrs = resource.attributes
        return Config(
            self,
            id=_unset_to_none(resource.id) or "",
            name=attrs.name,
            description=_unset_to_none(attrs.description),
            parent=_unset_to_none(attrs.parent),
            items=_extract_items(attrs.items),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


class AsyncConfigClient:
    """Asynchronous client for Smpl Config.

    Obtained via ``AsyncSmplClient(...).config``.
    """

    def __init__(self, parent: AsyncSmplClient) -> None:
        self._parent = parent
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []

    async def _connect_internal(self) -> None:
        """Fetch all configs, resolve values for the environment, and cache.

        Idempotent — returns immediately if already connected.
        """
        if self._connected:
            return
        configs = await self.list()
        environment = self._parent._environment
        cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = await cfg._build_chain(configs)
            cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            self._config_cache = cache
        self._connected = True

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def new(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        parent: str | None = None,
    ) -> AsyncConfig:
        """Return a new unsaved :class:`AsyncConfig`.

        Call :meth:`AsyncConfig.save` to persist it.

        Args:
            id: Config identifier (slug).
            name: Display name. Auto-generated from *id* if omitted.
            description: Optional description.
            parent: Parent config id (slug), or ``None``.

        Returns:
            A new :class:`AsyncConfig` that has not yet been saved.
        """
        return AsyncConfig(
            self,
            id=id,
            name=name or key_to_display_name(id),
            description=description,
            parent=parent,
        )

    async def get(self, id: str) -> AsyncConfig:
        """Fetch a config by id.

        Args:
            id: The config identifier (slug).

        Returns:
            The matching :class:`AsyncConfig`.

        Raises:
            SmplNotFoundError: If no matching config exists.
        """
        try:
            response = await get_config.asyncio_detailed(
                id,
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            raise SmplNotFoundError(f"Config with id '{id}' not found", status_code=404)
        return self._resource_to_model(response.parsed.data)

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

    async def delete(self, id: str) -> None:
        """Delete a config by id.

        Args:
            id: The config identifier (slug).

        Raises:
            SmplNotFoundError: If the config does not exist.
            SmplConflictError: If the config has children.
        """
        try:
            response = await delete_config.asyncio_detailed(
                id,
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    # ------------------------------------------------------------------
    # Runtime: resolve / subscribe
    # ------------------------------------------------------------------

    async def resolve(self, id: str, model: type | None = None) -> Any:
        """Return resolved config values for *id*.

        If *model* is ``None``, returns a flat ``dict[str, Any]`` of
        resolved values.

        If *model* is provided, dot-notation keys (e.g. ``"database.host"``)
        are expanded into nested structures and the model is constructed.
        Supports Pydantic models, dataclasses, or any class accepting
        keyword arguments.

        Args:
            id: The config id to resolve.
            model: Optional model class to construct from resolved values.

        Returns:
            A flat dict, or an instance of *model*.
        """
        await self._connect_internal()
        values = dict(self._config_cache.get(id, {}))
        metrics = self._parent._metrics
        if metrics is not None:
            metrics.record("config.resolutions", unit="resolutions", dimensions={"config": id})
        if model is None:
            return values
        nested = _unflatten(values)
        if hasattr(model, "model_validate"):
            return model.model_validate(nested)
        return model(**nested)

    async def subscribe(self, id: str, model: type | None = None) -> LiveConfigProxy:
        """Return a :class:`LiveConfigProxy` for *id*.

        Values update automatically after :meth:`refresh`.

        Args:
            id: The config id to subscribe to.
            model: Optional model class.

        Returns:
            A :class:`LiveConfigProxy`.
        """
        await self._connect_internal()
        return LiveConfigProxy(self, id, model)

    # ------------------------------------------------------------------
    # Runtime: refresh / change listeners
    # ------------------------------------------------------------------

    async def refresh(self) -> None:
        """Re-fetch all configs and update resolved values.

        Fires change listeners for any values that differ from the previous state.

        Raises:
            SmplConnectionError: If the fetch fails.
        """
        configs = await self.list()
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = await cfg._build_chain(configs)
            new_cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
        self._fire_change_listeners(old_cache, new_cache, source="manual")

    def on_change(
        self, fn_or_id: Callable[[ConfigChangeEvent], None] | str | None = None, *, item_key: str | None = None
    ) -> Any:
        """Register a change listener.

        Supports three forms:

        - ``@client.config.on_change`` — global listener (bare decorator).
        - ``@client.config.on_change("id")`` — config-scoped listener.
        - ``@client.config.on_change("id", item_key="field")`` — item-scoped.
        """
        if callable(fn_or_id):
            # @on_change (bare decorator)
            self._listeners.append((fn_or_id, None, None))
            return fn_or_id
        elif isinstance(fn_or_id, str):
            # @on_change("id") or @on_change("id", item_key="field")
            config_id = fn_or_id

            def decorator(fn: Callable[[ConfigChangeEvent], None]) -> Callable[[ConfigChangeEvent], None]:
                self._listeners.append((fn, config_id, item_key))
                return fn

            return decorator
        else:
            # @on_change() — called with parens but no args

            def decorator(fn: Callable[[ConfigChangeEvent], None]) -> Callable[[ConfigChangeEvent], None]:
                self._listeners.append((fn, None, None))
                return fn

            return decorator

    def _fire_change_listeners(
        self,
        old_cache: dict[str, dict[str, Any]],
        new_cache: dict[str, dict[str, Any]],
        *,
        source: str,
    ) -> None:
        """Diff two caches and fire listeners for any changed values."""
        all_config_ids = set(old_cache.keys()) | set(new_cache.keys())
        for cfg_id in all_config_ids:
            old_items = old_cache.get(cfg_id, {})
            new_items = new_cache.get(cfg_id, {})
            all_item_keys = set(old_items.keys()) | set(new_items.keys())
            for i_key in all_item_keys:
                old_val = old_items.get(i_key)
                new_val = new_items.get(i_key)
                if old_val == new_val:
                    continue
                metrics = self._parent._metrics
                if metrics is not None:
                    metrics.record("config.changes", unit="changes", dimensions={"config": cfg_id})
                event = ConfigChangeEvent(
                    config_id=cfg_id,
                    item_key=i_key,
                    old_value=old_val,
                    new_value=new_val,
                    source=source,
                )
                for callback, ck_filter, ik_filter in self._listeners:
                    if ck_filter is not None and ck_filter != cfg_id:
                        continue
                    if ik_filter is not None and ik_filter != i_key:
                        continue
                    try:
                        callback(event)
                    except Exception:
                        logger.error(
                            "Exception in on_change listener for %s.%s",
                            cfg_id,
                            i_key,
                            exc_info=True,
                        )

    # ------------------------------------------------------------------
    # Internal: create / update for AsyncConfig.save()
    # ------------------------------------------------------------------

    async def _create_config(self, config: AsyncConfig) -> AsyncConfig:
        """Internal: POST a new config from an AsyncConfig model (for AsyncConfig.save)."""
        body = _build_request_body(
            config_id=config.id,
            name=config.name,
            description=config.description,
            parent=config.parent,
            items=config._items_raw,
            environments=config.environments,
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
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._to_model(response.parsed)

    async def _update_config_from_model(self, config: AsyncConfig) -> AsyncConfig:
        """Internal: PUT a config update from an AsyncConfig model (for AsyncConfig.save)."""
        body = _build_request_body(
            config_id=config.id,
            name=config.name,
            description=config.description,
            parent=config.parent,
            items=config._items_raw,
            environments=config.environments,
        )
        try:
            response = await update_config.asyncio_detailed(
                config.id,
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._to_model(response.parsed)

    # ------------------------------------------------------------------
    # Internal: model conversion
    # ------------------------------------------------------------------

    def _to_model(self, parsed: Any) -> AsyncConfig:
        """Convert a ConfigResponse (single resource) to an AsyncConfig model."""
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> AsyncConfig:
        """Convert a ConfigResource to an AsyncConfig model."""
        attrs = resource.attributes
        return AsyncConfig(
            self,
            id=_unset_to_none(resource.id) or "",
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
