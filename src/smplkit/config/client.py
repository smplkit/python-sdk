"""ConfigClient and AsyncConfigClient — runtime operations for configs.

Runtime config operations: lazy-fetch all configs for the SDK's
current environment, resolve values down the inheritance chain, and
emit change events when the server's WebSocket signals a refresh.
CRUD lives on :class:`smplkit.SmplManagementClient`.
"""

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
from smplkit._resolver import resolve
from smplkit._generated.config.api.configs import (  # noqa: F401  (re-exported for test patches)
    create_config,
    delete_config,
    get_config,
    list_configs,
    update_config,
)
from smplkit.config.helpers import _resource_to_async_config, _resource_to_config
from smplkit.config.models import AsyncConfig, Config

if TYPE_CHECKING:
    from smplkit._ws import SharedWebSocket
    from smplkit.client import AsyncSmplClient, SmplClient

logger = logging.getLogger("smplkit")
ws_logger = logging.getLogger("smplkit.config.ws")


def _check_response_status(status_code: HTTPStatus, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


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


def _build_chain_sync(model: Any, models_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a parent chain from pre-fetched models without async calls."""
    chain = [{"id": model.id, "items": model._items_raw, "environments": model.environments}]
    current = model
    while current.parent is not None:
        parent = models_by_id.get(current.parent)
        if parent is None:
            break
        chain.append({"id": parent.id, "items": parent._items_raw, "environments": parent.environments})
        current = parent
    return chain


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
    """Synchronous runtime client for Smpl Config.

    Obtained via ``SmplClient(...).config``. Exposes value resolution
    (``get``/``subscribe``) and refresh/change-listener APIs. CRUD has
    moved to :class:`smplkit.SmplManagementClient` (``mgmt.configs.*``).
    """

    def __init__(self, parent: SmplClient) -> None:
        self._parent = parent
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._raw_config_cache: dict[str, Any] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []
        self._ws_manager: SharedWebSocket | None = None

    def _connect_internal(self) -> None:
        """Fetch all configs, resolve values for the environment, and cache.

        Idempotent — returns immediately if already connected.
        """
        if self._connected:
            return
        configs = self._fetch_all_configs()
        environment = self._parent._environment
        cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = cfg._build_chain(configs)
            cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            self._config_cache = cache
            self._raw_config_cache = {cfg.id: cfg for cfg in configs}
        self._connected = True

        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("config_changed", self._handle_config_changed)
        self._ws_manager.on("config_deleted", self._handle_config_deleted)
        self._ws_manager.on("configs_changed", self._handle_configs_changed)

    def _fetch_all_configs(self) -> list[Config]:
        """List configs directly from the API (no management indirection)."""
        try:
            response = list_configs.sync_detailed(client=self._parent._http_client)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._http_client._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [_resource_to_config(None, r) for r in response.parsed.data]

    def _fetch_config(self, config_id: str) -> Config | None:
        """Fetch a single config from the API. Returns ``None`` on missing data."""
        try:
            response = get_config.sync_detailed(config_id, client=self._parent._http_client)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._http_client._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return None
        return _resource_to_config(None, response.parsed.data)

    # ------------------------------------------------------------------
    # Runtime: get / subscribe
    # ------------------------------------------------------------------

    def get(self, id: str, model: type | None = None) -> Any:
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
        self._do_refresh("manual")

    def _do_refresh(self, source: str) -> None:
        configs = self._fetch_all_configs()
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = cfg._build_chain(configs)
            new_cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
            self._raw_config_cache = {cfg.id: cfg for cfg in configs}
        self._fire_change_listeners(old_cache, new_cache, source=source)

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
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_config_changed(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        environment = self._parent._environment
        with self._cache_lock:
            old_values = dict(self._config_cache.get(key, {}))
            raw_cache = dict(self._raw_config_cache)
        try:
            cfg = self._fetch_config(key)
        except Exception:
            ws_logger.error("Failed to fetch config %r after WS event", key, exc_info=True)
            return
        if cfg is None:
            return
        raw_cache[key] = cfg
        chain = cfg._build_chain(list(raw_cache.values()))
        new_values = resolve(chain, environment)
        with self._cache_lock:
            self._raw_config_cache[key] = cfg
            self._config_cache[key] = new_values
        old_partial = {key: old_values}
        new_partial = {key: new_values}
        self._fire_change_listeners(old_partial, new_partial, source="websocket")

    def _handle_config_deleted(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        with self._cache_lock:
            old_values = dict(self._config_cache.pop(key, {}))
            self._raw_config_cache.pop(key, None)
        if old_values:
            old_partial = {key: old_values}
            new_partial: dict[str, dict[str, Any]] = {}
            self._fire_change_listeners(old_partial, new_partial, source="websocket")

    def _handle_configs_changed(self, data: dict[str, Any]) -> None:
        try:
            self._do_refresh("websocket")
        except Exception:
            ws_logger.error("Failed to refresh configs after WS event", exc_info=True)


class AsyncConfigClient:
    """Asynchronous runtime client for Smpl Config.

    Obtained via ``AsyncSmplClient(...).config``. CRUD has moved to
    :class:`smplkit.AsyncSmplManagementClient` (``mgmt.configs.*``).
    """

    def __init__(self, parent: AsyncSmplClient) -> None:
        self._parent = parent
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._raw_config_cache: dict[str, Any] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []
        self._ws_manager: SharedWebSocket | None = None

    async def _connect_internal(self) -> None:
        """Fetch all configs, resolve values for the environment, and cache.

        Idempotent — returns immediately if already connected.
        """
        if self._connected:
            return
        configs = await self._fetch_all_configs_async()
        environment = self._parent._environment
        cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = await cfg._build_chain(configs)
            cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            self._config_cache = cache
            self._raw_config_cache = {cfg.id: cfg for cfg in configs}
        self._connected = True

        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("config_changed", self._handle_config_changed)
        self._ws_manager.on("config_deleted", self._handle_config_deleted)
        self._ws_manager.on("configs_changed", self._handle_configs_changed)

    async def _fetch_all_configs_async(self) -> list[AsyncConfig]:
        try:
            response = await list_configs.asyncio_detailed(client=self._parent._http_client)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._http_client._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [_resource_to_async_config(None, r) for r in response.parsed.data]

    # ------------------------------------------------------------------
    # Runtime: get / subscribe
    # ------------------------------------------------------------------

    async def get(self, id: str, model: type | None = None) -> Any:
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
        await self._do_refresh("manual")

    async def _do_refresh(self, source: str) -> None:
        configs = await self._fetch_all_configs_async()
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg in configs:
            chain = await cfg._build_chain(configs)
            new_cache[cfg.id] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
            self._raw_config_cache = {cfg.id: cfg for cfg in configs}
        self._fire_change_listeners(old_cache, new_cache, source=source)

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
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_config_changed(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        environment = self._parent._environment
        with self._cache_lock:
            old_values = dict(self._config_cache.get(key, {}))
            raw_cache = dict(self._raw_config_cache)
        try:
            response = get_config.sync_detailed(key, client=self._parent._http_client)
            _check_response_status(response.status_code, response.content)
            if response.parsed is None or not hasattr(response.parsed, "data"):
                return
            cfg = _resource_to_async_config(None, response.parsed.data)
        except Exception:
            ws_logger.error("Failed to fetch config %r after WS event", key, exc_info=True)
            return
        raw_cache[key] = cfg
        chain = _build_chain_sync(cfg, raw_cache)
        new_values = resolve(chain, environment)
        with self._cache_lock:
            self._raw_config_cache[key] = cfg
            self._config_cache[key] = new_values
        old_partial = {key: old_values}
        new_partial = {key: new_values}
        self._fire_change_listeners(old_partial, new_partial, source="websocket")

    def _handle_config_deleted(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        with self._cache_lock:
            old_values = dict(self._config_cache.pop(key, {}))
            self._raw_config_cache.pop(key, None)
        if old_values:
            old_partial = {key: old_values}
            new_partial: dict[str, dict[str, Any]] = {}
            self._fire_change_listeners(old_partial, new_partial, source="websocket")

    def _handle_configs_changed(self, data: dict[str, Any]) -> None:
        try:
            response = list_configs.sync_detailed(client=self._parent._http_client)
            _check_response_status(response.status_code, response.content)
            if response.parsed is None or not hasattr(response.parsed, "data"):
                return
            models = [_resource_to_async_config(None, r) for r in response.parsed.data]
            environment = self._parent._environment
            models_by_id = {m.id: m for m in models}
            new_cache: dict[str, dict[str, Any]] = {}
            for m in models:
                chain = _build_chain_sync(m, models_by_id)
                new_cache[m.id] = resolve(chain, environment)
            with self._cache_lock:
                old_cache = self._config_cache
                self._config_cache = new_cache
                self._raw_config_cache = models_by_id
            self._fire_change_listeners(old_cache, new_cache, source="websocket")
        except Exception:
            ws_logger.error("Failed to refresh configs after WS event", exc_info=True)


def _exc_url(exc: Exception) -> str | None:
    """Extract URL from an httpx exception's associated request, if available."""
    try:
        return str(exc.request.url)  # type: ignore[attr-defined]
    except Exception:
        return None


def _maybe_reraise_network_error(exc: Exception, base_url: str | None = None) -> None:
    """Re-raise httpx exceptions as SDK exceptions if applicable.

    Args:
        exc: The exception to inspect.
        base_url: Fallback URL to include in the error message when the exception
            does not carry request context (e.g. DNS failures before a request
            object is attached by httpx).
    """
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        url = _exc_url(exc) or base_url
        msg = f"Request timed out connecting to {url}" if url else f"Request timed out: {exc}"
        raise SmplTimeoutError(msg) from exc
    if isinstance(exc, httpx.HTTPError):
        url = _exc_url(exc) or base_url
        msg = f"Cannot connect to {url}: {exc}" if url else f"Connection error: {exc}"
        raise SmplConnectionError(msg) from exc
    if isinstance(exc, (SmplNotFoundError, SmplConflictError, SmplValidationError)):
        raise exc
