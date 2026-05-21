"""ConfigClient and AsyncConfigClient — runtime operations for configs.

Runtime config operations: lazy-fetch all configs for the SDK's
current environment, resolve values down the inheritance chain, and
emit change events when the server's WebSocket signals a refresh.
CRUD lives on :class:`smplkit.SmplManagementClient`.
"""

from __future__ import annotations


import dataclasses
import logging
import threading
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeVar, overload

from smplkit._errors import (
    ConflictError,
    ConnectionError,
    NotFoundError,
    TimeoutError,
    ValidationError,
    _raise_for_status,
)
from smplkit._helpers import PAGE_SIZE, paginate_async, paginate_sync
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
    from smplkit._metrics import _AsyncMetricsReporter, _MetricsReporter
    from smplkit._ws import SharedWebSocket
    from smplkit.client import AsyncSmplClient, SmplClient
    from smplkit.management.client import AsyncSmplManagementClient, SmplManagementClient

logger = logging.getLogger("smplkit")
ws_logger = logging.getLogger("smplkit.config.ws")

# Type var for the optional ``model`` arg on get() — lets customers see
# ``cfg: UserServiceConfig`` in their IDE rather than ``LiveConfigProxy``
# when they pass a model class.
_M = TypeVar("_M")


def _check_response_status(status_code: HTTPStatus, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


def _pydantic_field_type(annotation: Any) -> str:
    """Map a Pydantic field annotation to a smplkit Config item type.

    Falls back to ``JSON`` for any annotation that isn't a clear scalar —
    including unions, lists, dicts, and unknown types. The server treats
    JSON as an escape hatch (ADR-024 §2.5).
    """
    if annotation is bool:
        return "BOOLEAN"
    if annotation is int or annotation is float:
        return "NUMBER"
    if annotation is str:
        return "STRING"
    return "JSON"


def _is_pydantic_model(cls: Any) -> bool:
    return isinstance(cls, type) and hasattr(cls, "model_fields") and hasattr(cls, "model_validate")


def _iter_pydantic_items(model: type, prefix: str = "") -> list[tuple[str, str, Any, str | None]]:
    """Walk a Pydantic model's fields and yield ``(key, type, default, description)`` tuples.

    Nested Pydantic models flatten to dot-notation. A field whose default
    is :data:`pydantic.fields.PydanticUndefined` is skipped — the SDK
    has no value to register. Pydantic-aware callers are encouraged to
    declare a sensible default on every field so the registration
    payload is complete.
    """
    if not _is_pydantic_model(model):
        return []

    try:
        from pydantic.fields import PydanticUndefined
    except ImportError:  # pragma: no cover - pydantic always present
        PydanticUndefined = object()  # type: ignore[assignment]

    items: list[tuple[str, str, Any, str | None]] = []
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        flat_key = f"{prefix}{field_name}"

        if _is_pydantic_model(annotation):
            items.extend(_iter_pydantic_items(annotation, prefix=f"{flat_key}."))
            continue

        if field_info.default is not PydanticUndefined:
            default = field_info.default
        elif field_info.default_factory is not None:
            try:
                default = field_info.default_factory()
            except Exception:
                continue
        else:
            continue

        item_type = _pydantic_field_type(annotation)
        description = field_info.description
        items.append((flat_key, item_type, default, description))

    return items


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
    from smplkit.config.models import _environments_to_wire

    chain = [
        {
            "id": model.id,
            "items": model._items_raw,
            "environments": _environments_to_wire(model._environments),
        }
    ]
    current = model
    while current.parent is not None:
        parent = models_by_id.get(current.parent)
        if parent is None:
            break
        chain.append(
            {
                "id": parent.id,
                "items": parent._items_raw,
                "environments": _environments_to_wire(parent._environments),
            }
        )
        current = parent
    return chain


@dataclasses.dataclass(frozen=True, kw_only=True)
class ConfigChangeEvent:
    """Describes a single config value change.

    Frozen — fields are set at construction and cannot be mutated afterward.

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


class LiveConfigProxy:
    """A live, dict-like view of resolved config values.

    Returned by :meth:`ConfigClient.get` and :meth:`AsyncConfigClient.get`.
    Always reflects the latest server-pushed state — every read sees
    current values.

    Attribute access returns the current resolved value for the given
    item key. If a *model* was provided, the model is reconstructed
    from the latest values on each access (so attribute access type-checks
    against the model).

    Also implements the standard ``Mapping`` API: ``proxy["key"]``,
    ``key in proxy``, ``len(proxy)``, ``for k in proxy``, ``proxy.keys()``,
    ``proxy.values()``, ``proxy.items()``, ``proxy.get(key, default)``.

    Note: customer config items whose names collide with dict-method names
    (``keys``, ``values``, ``items``, ``get``) are shadowed for attribute
    access — use subscript (``proxy["values"]``) for those.
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

    def on_change(self, fn_or_key: Callable[[ConfigChangeEvent], None] | str | None = None) -> Any:
        """Register a change listener scoped to this config.

        Supports three forms:

        - ``@proxy.on_change`` — fires on any change to this config.
        - ``@proxy.on_change("item_key")`` — fires only when ``item_key`` changes.
        - ``@proxy.on_change()`` — same as the bare-decorator form.

        Equivalent to ``client.config.on_change(self._config_id, ...)``;
        offered as sugar so customers who already have a live proxy can
        register listeners without re-stating the config id.
        """
        client = object.__getattribute__(self, "_client")
        config_id = object.__getattribute__(self, "_config_id")
        if callable(fn_or_key):
            return client.on_change(config_id)(fn_or_key)
        if isinstance(fn_or_key, str):
            return client.on_change(config_id, item_key=fn_or_key)
        return client.on_change(config_id)

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

    def __iter__(self):
        return iter(self._current_values())

    def __contains__(self, key: object) -> bool:
        return key in self._current_values()

    def __len__(self) -> int:
        return len(self._current_values())

    def keys(self):
        return self._current_values().keys()

    def values(self):
        return self._current_values().values()

    def items(self):
        return self._current_values().items()

    def get(self, key: str, default: Any = None) -> Any:
        return self._current_values().get(key, default)

    # ------------------------------------------------------------------
    # Typed getters (ADR-037 §2.13)
    #
    # Each registers the item (key, type, default, description) on first
    # call within the process, then returns the resolved value. When the
    # resolved value cannot be coerced to the getter's type — including
    # the "not yet set on the server" case — the in-code default is
    # returned and a structured warning is logged. See ADR-024 §2.5.
    # ------------------------------------------------------------------

    def _register_item(self, item_key: str, item_type: str, default: Any, description: str | None) -> None:
        client = object.__getattribute__(self, "_client")
        config_id = object.__getattribute__(self, "_config_id")
        client._observe_item_declaration(config_id, item_key, item_type, default, description)

    def get_bool(self, key: str, default: bool, *, description: str | None = None) -> bool:
        """Read a BOOLEAN item, registering the declaration on first call."""
        self._register_item(key, "BOOLEAN", default, description)
        values = self._current_values()
        if key not in values:
            return default
        value = values[key]
        if isinstance(value, bool):
            return value
        config_id = object.__getattribute__(self, "_config_id")
        logger.warning(
            "config %r item %r: expected BOOLEAN, got %s; returning default",
            config_id,
            key,
            type(value).__name__,
        )
        return default

    def get_int(self, key: str, default: int, *, description: str | None = None) -> int:
        """Read a NUMBER item as int, registering the declaration on first call."""
        self._register_item(key, "NUMBER", default, description)
        values = self._current_values()
        if key not in values:
            return default
        value = values[key]
        # bool is a subclass of int in Python; reject it explicitly.
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        config_id = object.__getattribute__(self, "_config_id")
        logger.warning(
            "config %r item %r: expected NUMBER (int), got %s; returning default",
            config_id,
            key,
            type(value).__name__,
        )
        return default

    def get_float(self, key: str, default: float, *, description: str | None = None) -> float:
        """Read a NUMBER item as float, registering the declaration on first call."""
        self._register_item(key, "NUMBER", default, description)
        values = self._current_values()
        if key not in values:
            return default
        value = values[key]
        if isinstance(value, bool):
            # bool is technically int|number but typed-float expects a numeric.
            config_id = object.__getattribute__(self, "_config_id")
            logger.warning(
                "config %r item %r: expected NUMBER (float), got bool; returning default",
                config_id,
                key,
            )
            return default
        if isinstance(value, (int, float)):
            return float(value)
        config_id = object.__getattribute__(self, "_config_id")
        logger.warning(
            "config %r item %r: expected NUMBER (float), got %s; returning default",
            config_id,
            key,
            type(value).__name__,
        )
        return default

    def get_string(self, key: str, default: str, *, description: str | None = None) -> str:
        """Read a STRING item, registering the declaration on first call."""
        self._register_item(key, "STRING", default, description)
        values = self._current_values()
        if key not in values:
            return default
        value = values[key]
        if isinstance(value, str):
            return value
        config_id = object.__getattribute__(self, "_config_id")
        logger.warning(
            "config %r item %r: expected STRING, got %s; returning default",
            config_id,
            key,
            type(value).__name__,
        )
        return default

    def get_json(self, key: str, default: Any, *, description: str | None = None) -> Any:
        """Read a JSON item, registering the declaration on first call.

        Unlike the other typed getters, ``get_json`` accepts any JSON
        value type — its purpose is escape-hatch storage for arbitrary
        structured payloads (ADR-024 §2.5).
        """
        self._register_item(key, "JSON", default, description)
        values = self._current_values()
        if key not in values:
            return default
        return values[key]

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"LiveConfigProxy is read-only; cannot set {name!r}. Mutate config values via client.manage.config.*"
        )

    def __setitem__(self, key: str, value: Any) -> None:
        raise TypeError(
            f"LiveConfigProxy is read-only; cannot set {key!r}. Mutate config values via client.manage.config.*"
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"LiveConfigProxy is read-only; cannot delete {name!r}.")

    def __delitem__(self, key: str) -> None:
        raise TypeError(f"LiveConfigProxy is read-only; cannot delete {key!r}.")

    def __repr__(self) -> str:
        config_id = object.__getattribute__(self, "_config_id")
        model = object.__getattribute__(self, "_model")
        if model is not None:
            return f"LiveConfigProxy(config_id={config_id!r}, model={model.__name__})"
        return f"LiveConfigProxy(config_id={config_id!r})"


class ConfigClient:
    """Synchronous runtime client for Smpl Config.

    Obtained via ``SmplClient(...).config``. Exposes value resolution
    (``get``) and refresh/change-listener APIs. CRUD has
    moved to :class:`smplkit.SmplManagementClient` (``mgmt.config.*``).
    """

    def __init__(
        self,
        parent: SmplClient,
        *,
        manage: SmplManagementClient,
        metrics: _MetricsReporter | None,
    ) -> None:
        self._parent = parent
        self._manage = manage
        self._metrics = metrics
        self._service = parent._service
        self._environment = parent._environment
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._raw_config_cache: dict[str, Any] = {}
        # Cache of declared/fetched LiveConfigProxy instances so repeat
        # `get_or_create(id)` (or `get(id)` after discovery) calls return the
        # same object — enabling inheritance via direct handle references per
        # ADR-037 §2.13.
        self._proxies: dict[str, LiveConfigProxy] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []
        self._ws_manager: SharedWebSocket | None = None

    def start(self) -> None:
        """Eagerly initialize the config subclient.

        Fetches all configs, resolves environment-scoped values into the local
        cache, opens the shared WebSocket and subscribes to ``config_changed``
        / ``config_deleted`` / ``configs_changed`` events.

        Idempotent — safe to call multiple times.  Called automatically on
        first ``config.get()`` if not invoked manually.
        """
        if self._connected:
            return

        # Per ADR-037 §2.14: flush any buffered discovery declarations BEFORE
        # the initial fetch, so newly-discovered configs appear in the cache.
        try:
            self._manage.config.flush()
        except Exception as exc:
            logger.warning("Pre-start config discovery flush failed: %s", exc)

        # Fetch + resolve + cache + fire change listeners (against empty old_cache,
        # so any registered listeners see "initial" events).
        self._do_refresh("initial")
        self._connected = True

        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("config_changed", self._handle_config_changed)
        self._ws_manager.on("config_deleted", self._handle_config_deleted)
        self._ws_manager.on("configs_changed", self._handle_configs_changed)

    def _fetch_all_configs(self) -> list[Config]:
        """List configs directly from the API (no management indirection)."""

        def fetch_page(page_number: int, page_size: int) -> list[Config]:
            try:
                response = list_configs.sync_detailed(
                    client=self._parent._http_client,
                    pagenumber=page_number,
                    pagesize=page_size,
                )
            except Exception as exc:
                _maybe_reraise_network_error(exc, self._parent._http_client._base_url)
                raise
            _check_response_status(response.status_code, response.content)
            if response.parsed is None or not hasattr(response.parsed, "data"):
                return []
            return [_resource_to_config(None, r) for r in response.parsed.data]

        return paginate_sync(fetch_page)

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
    # Runtime: get
    # ------------------------------------------------------------------

    @overload
    def get(self, id: str) -> LiveConfigProxy: ...
    @overload
    def get(self, id: str, model: type[_M]) -> _M: ...
    def get(self, id: str, model: type[_M] | None = None) -> Any:
        """Return a live, dict-like view of the resolved values for *id*.

        Without ``model``, returns a :class:`LiveConfigProxy` that behaves
        like a ``dict[str, Any]`` (``proxy["key"]``, iteration, ``items()``,
        ``len()``) and updates automatically as the server pushes changes.

        With ``model``, the return value type-checks as *model* — attribute
        access (``cfg.database.host``) walks a model rebuilt from the
        current values on each read, so the customer sees the model's
        type signature in their IDE while still tracking live data.

        Args:
            id: The config id to resolve.
            model: Optional model class to project attribute access through.

        Returns:
            A :class:`LiveConfigProxy` (typed as *model* when supplied).

        Raises:
            NotFoundError: If no config with the given id exists. The check
                runs against the cache populated by :meth:`start`, which is
                kept current by WebSocket events; call :meth:`refresh` if a
                config was just created out-of-band and may not yet be visible.
        """
        self.start()
        if id not in self._config_cache:
            raise NotFoundError(f"Config with id '{id}' not found", status_code=404)
        metrics = self._metrics
        if metrics is not None:
            metrics.record("config.resolutions", unit="resolutions", dimensions={"config": id})
        return self._cached_proxy(id, model)

    def get_or_create(
        self,
        id: str,
        *,
        parent: str | LiveConfigProxy | None = None,
        name: str | None = None,
        description: str | None = None,
        model: type[_M] | None = None,
    ) -> LiveConfigProxy:
        """Declare a configuration from code; return a live, dict-like view.

        Idempotent. Repeated calls with the same ``id`` return the same
        :class:`LiveConfigProxy` instance. The first call queues a
        discovery payload (the config and any items declared via typed
        getters on the returned handle) for upload to
        ``POST /api/v1/configs/bulk`` on next flush. If the config already
        exists server-side, ``managed=true`` configs are left untouched;
        ``managed=false`` configs receive the SDK's items via source-row
        upsert per ADR-024 §2.9.

        Unlike :meth:`get`, this method **does not raise** ``NotFoundError``
        when the id is absent from the cache — discovery handles that case.

        Args:
            id: The config id to declare.
            parent: Optional parent reference, either as a string id or as
                a :class:`LiveConfigProxy` returned by a prior call to
                ``get_or_create``. Enables inheritance declared via direct
                object references.
            name: Optional display name (defaults to a humanized id).
            description: Optional description.
            model: Optional Pydantic model whose ``model_fields`` are
                introspected to register every field as a typed item in
                one batched payload. Nested models flatten to
                dot-notation keys.

        Returns:
            A :class:`LiveConfigProxy` for the declared id.
        """
        parent_id: str | None
        if isinstance(parent, LiveConfigProxy):
            parent_id = object.__getattribute__(parent, "_config_id")
        else:
            parent_id = parent

        self._observe_config_declaration(id, parent=parent_id, name=name, description=description)

        if model is not None:
            for item_key, item_type, default, item_description in _iter_pydantic_items(model):
                self._observe_item_declaration(id, item_key, item_type, default, item_description)

        # Ensure lazy init runs at least once so the cache reflects the
        # newly-declared config (post-flush) on the very first read.
        self.start()
        return self._cached_proxy(id, model)

    def _cached_proxy(self, id: str, model: type[_M] | None) -> LiveConfigProxy:
        """Return (and cache) the canonical proxy for a config id."""
        proxy = self._proxies.get(id)
        if proxy is None:
            proxy = LiveConfigProxy(self, id, model)
            self._proxies[id] = proxy
        elif model is not None and object.__getattribute__(proxy, "_model") is None:
            # First model-typed access — upgrade the proxy in place so
            # subsequent attribute access returns the typed view.
            object.__setattr__(proxy, "_model", model)
        return proxy

    def _observe_config_declaration(
        self,
        config_id: str,
        *,
        parent: str | None,
        name: str | None,
        description: str | None,
    ) -> None:
        """Queue a config declaration with the management buffer."""
        self._manage.config.register_config(
            config_id,
            service=self._service,
            environment=self._environment,
            parent=parent,
            name=name,
            description=description,
        )

    def _observe_item_declaration(
        self,
        config_id: str,
        item_key: str,
        item_type: str,
        default: Any,
        description: str | None,
    ) -> None:
        """Queue a config item declaration with the management buffer."""
        self._manage.config.register_config_item(config_id, item_key, item_type, default, description)

    # ------------------------------------------------------------------
    # Runtime: refresh / change listeners
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Re-fetch all configs and update resolved values.

        Fires change listeners for any values that differ from the previous state.

        Raises:
            ConnectionError: If the fetch fails.
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
                metrics = self._metrics
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

    def _rebuild_resolved_cache(self, raw_cache: dict[str, Config], source: str) -> None:
        """Re-resolve every config in ``raw_cache`` and fire change listeners.

        Inheritance means a single config change can shift descendants' resolved
        values too — so whenever ``raw_cache`` is mutated (config added, updated,
        or deleted), every config gets re-resolved against the new snapshot.
        """
        environment = self._parent._environment
        raw_list = list(raw_cache.values())
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg_id, cfg in raw_cache.items():
            chain = cfg._build_chain(raw_list)
            new_cache[cfg_id] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
            self._raw_config_cache = raw_cache
        self._fire_change_listeners(old_cache, new_cache, source=source)

    def _handle_config_changed(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        with self._cache_lock:
            raw_cache = dict(self._raw_config_cache)
        try:
            cfg = self._fetch_config(key)
        except Exception:
            ws_logger.error("Failed to fetch config %r after WS event", key, exc_info=True)
            return
        if cfg is None:
            return
        raw_cache[key] = cfg
        self._rebuild_resolved_cache(raw_cache, source="websocket")

    def _handle_config_deleted(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        with self._cache_lock:
            raw_cache = dict(self._raw_config_cache)
        if raw_cache.pop(key, None) is None:
            return
        self._rebuild_resolved_cache(raw_cache, source="websocket")

    def _handle_configs_changed(self, data: dict[str, Any]) -> None:
        try:
            self._do_refresh("websocket")
        except Exception:
            ws_logger.error("Failed to refresh configs after WS event", exc_info=True)


class AsyncConfigClient:
    """Asynchronous runtime client for Smpl Config.

    Obtained via ``AsyncSmplClient(...).config``. CRUD has moved to
    :class:`smplkit.AsyncSmplManagementClient` (``mgmt.config.*``).
    """

    def __init__(
        self,
        parent: AsyncSmplClient,
        *,
        manage: AsyncSmplManagementClient,
        metrics: _AsyncMetricsReporter | None,
    ) -> None:
        self._parent = parent
        self._manage = manage
        self._metrics = metrics
        self._service = parent._service
        self._environment = parent._environment
        self._config_cache: dict[str, dict[str, Any]] = {}
        self._raw_config_cache: dict[str, Any] = {}
        # Cache of declared/fetched LiveConfigProxy instances so repeat
        # `get_or_create(id)` calls return the same object (per ADR-037 §2.13).
        self._proxies: dict[str, LiveConfigProxy] = {}
        self._connected = False
        self._cache_lock = threading.Lock()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None, str | None]] = []
        self._ws_manager: SharedWebSocket | None = None

    async def start(self) -> None:
        """Eagerly initialize the config subclient.

        Fetches all configs, resolves environment-scoped values into the local
        cache, opens the shared WebSocket and subscribes to ``config_changed``
        / ``config_deleted`` / ``configs_changed`` events.

        Idempotent — safe to call multiple times.  Called automatically on
        first ``config.get()`` if not invoked manually.
        """
        if self._connected:
            return

        # Per ADR-037 §2.14: flush any buffered discovery declarations BEFORE
        # the initial fetch so newly-discovered configs appear in the cache.
        try:
            await self._manage.config.flush()
        except Exception as exc:
            logger.warning("Pre-start config discovery flush failed: %s", exc)

        # Fetch + resolve + cache + fire change listeners (against empty old_cache,
        # so any registered listeners see "initial" events).
        await self._do_refresh("initial")
        self._connected = True

        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("config_changed", self._handle_config_changed)
        self._ws_manager.on("config_deleted", self._handle_config_deleted)
        self._ws_manager.on("configs_changed", self._handle_configs_changed)

    async def _fetch_all_configs_async(self) -> list[AsyncConfig]:
        async def fetch_page(page_number: int, page_size: int) -> list[AsyncConfig]:
            try:
                response = await list_configs.asyncio_detailed(
                    client=self._parent._http_client,
                    pagenumber=page_number,
                    pagesize=page_size,
                )
            except Exception as exc:
                _maybe_reraise_network_error(exc, self._parent._http_client._base_url)
                raise
            _check_response_status(response.status_code, response.content)
            if response.parsed is None or not hasattr(response.parsed, "data"):
                return []
            return [_resource_to_async_config(None, r) for r in response.parsed.data]

        return await paginate_async(fetch_page)

    # ------------------------------------------------------------------
    # Runtime: get
    # ------------------------------------------------------------------

    @overload
    async def get(self, id: str) -> LiveConfigProxy: ...
    @overload
    async def get(self, id: str, model: type[_M]) -> _M: ...
    async def get(self, id: str, model: type[_M] | None = None) -> Any:
        """Return a live, dict-like view of the resolved values for *id*.

        Without ``model``, returns a :class:`LiveConfigProxy` that behaves
        like a ``dict[str, Any]`` and updates automatically as the server
        pushes changes.

        With ``model``, the return value type-checks as *model* — attribute
        access walks a model rebuilt from the current values on each read.

        Args:
            id: The config id to resolve.
            model: Optional model class to project attribute access through.

        Returns:
            A :class:`LiveConfigProxy` (typed as *model* when supplied).

        Raises:
            NotFoundError: If no config with the given id exists. The check
                runs against the cache populated by :meth:`start`, which is
                kept current by WebSocket events; call :meth:`refresh` if a
                config was just created out-of-band and may not yet be visible.
        """
        await self.start()
        if id not in self._config_cache:
            raise NotFoundError(f"Config with id '{id}' not found", status_code=404)
        metrics = self._metrics
        if metrics is not None:
            metrics.record("config.resolutions", unit="resolutions", dimensions={"config": id})
        return self._cached_proxy(id, model)

    async def get_or_create(
        self,
        id: str,
        *,
        parent: str | LiveConfigProxy | None = None,
        name: str | None = None,
        description: str | None = None,
        model: type[_M] | None = None,
    ) -> LiveConfigProxy:
        """Declare a configuration from code; return a live, dict-like view.

        See :meth:`ConfigClient.get_or_create` for the full contract.
        Idempotent: repeated calls with the same ``id`` return the same
        proxy instance. Does not raise on missing id — discovery handles
        the create case.
        """
        parent_id: str | None
        if isinstance(parent, LiveConfigProxy):
            parent_id = object.__getattribute__(parent, "_config_id")
        else:
            parent_id = parent

        self._observe_config_declaration(id, parent=parent_id, name=name, description=description)

        if model is not None:
            for item_key, item_type, default, item_description in _iter_pydantic_items(model):
                self._observe_item_declaration(id, item_key, item_type, default, item_description)

        await self.start()
        return self._cached_proxy(id, model)

    def _cached_proxy(self, id: str, model: type[_M] | None) -> LiveConfigProxy:
        proxy = self._proxies.get(id)
        if proxy is None:
            proxy = LiveConfigProxy(self, id, model)
            self._proxies[id] = proxy
        elif model is not None and object.__getattribute__(proxy, "_model") is None:
            object.__setattr__(proxy, "_model", model)
        return proxy

    def _observe_config_declaration(
        self,
        config_id: str,
        *,
        parent: str | None,
        name: str | None,
        description: str | None,
    ) -> None:
        self._manage.config.register_config(
            config_id,
            service=self._service,
            environment=self._environment,
            parent=parent,
            name=name,
            description=description,
        )

    def _observe_item_declaration(
        self,
        config_id: str,
        item_key: str,
        item_type: str,
        default: Any,
        description: str | None,
    ) -> None:
        self._manage.config.register_config_item(config_id, item_key, item_type, default, description)

    # ------------------------------------------------------------------
    # Runtime: refresh / change listeners
    # ------------------------------------------------------------------

    async def refresh(self) -> None:
        """Re-fetch all configs and update resolved values.

        Fires change listeners for any values that differ from the previous state.

        Raises:
            ConnectionError: If the fetch fails.
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
                metrics = self._metrics
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

    def _rebuild_resolved_cache(self, raw_cache: dict[str, AsyncConfig], source: str) -> None:
        """Re-resolve every config in ``raw_cache`` and fire change listeners.

        Inheritance means a single config change can shift descendants' resolved
        values too — so whenever ``raw_cache`` is mutated (config added, updated,
        or deleted), every config gets re-resolved against the new snapshot.

        Sync-shaped because the WS dispatch thread is sync; ``_build_chain_sync``
        avoids any awaits and works against the already-loaded models.
        """
        environment = self._parent._environment
        new_cache: dict[str, dict[str, Any]] = {}
        for cfg_id, cfg in raw_cache.items():
            chain = _build_chain_sync(cfg, raw_cache)
            new_cache[cfg_id] = resolve(chain, environment)
        with self._cache_lock:
            old_cache = self._config_cache
            self._config_cache = new_cache
            self._raw_config_cache = raw_cache
        self._fire_change_listeners(old_cache, new_cache, source=source)

    def _handle_config_changed(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        with self._cache_lock:
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
        self._rebuild_resolved_cache(raw_cache, source="websocket")

    def _handle_config_deleted(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            self._handle_configs_changed(data)
            return
        with self._cache_lock:
            raw_cache = dict(self._raw_config_cache)
        if raw_cache.pop(key, None) is None:
            return
        self._rebuild_resolved_cache(raw_cache, source="websocket")

    def _handle_configs_changed(self, data: dict[str, Any]) -> None:
        try:
            models: list[AsyncConfig] = []
            page = 1
            while True:
                response = list_configs.sync_detailed(
                    client=self._parent._http_client,
                    pagenumber=page,
                    pagesize=PAGE_SIZE,
                )
                _check_response_status(response.status_code, response.content)
                if response.parsed is None or not hasattr(response.parsed, "data"):
                    # Malformed response — preserve the existing cache rather
                    # than risk wiping it from a partial refresh.
                    return
                page_rows = [_resource_to_async_config(None, r) for r in response.parsed.data]
                models.extend(page_rows)
                if len(page_rows) < PAGE_SIZE:
                    break
                page += 1
            raw_cache = {m.id: m for m in models}
            self._rebuild_resolved_cache(raw_cache, source="websocket")
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
        raise TimeoutError(msg) from exc
    if isinstance(exc, httpx.HTTPError):
        url = _exc_url(exc) or base_url
        msg = f"Cannot connect to {url}: {exc}" if url else f"Connection error: {exc}"
        raise ConnectionError(msg) from exc
    if isinstance(exc, (NotFoundError, ConflictError, ValidationError)):
        raise exc
