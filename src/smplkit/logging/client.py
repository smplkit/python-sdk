"""LoggingClient and AsyncLoggingClient — runtime control for Smpl Logging.

Runtime: discover loggers via adapters, register them with the
service, fetch resolved levels, and apply them. CRUD has moved to
:class:`smplkit.SmplManagementClient` (``mgmt.loggers.*`` / ``mgmt.log_groups.*``).
"""

from __future__ import annotations

import dataclasses
import importlib
import logging as stdlib_logging
import threading
import traceback
from typing import TYPE_CHECKING, Any, Callable

from smplkit._debug import debug
from smplkit._errors import (
    ConflictError,
    ConnectionError,
    NotFoundError,
    TimeoutError,
    ValidationError,
    _raise_for_status,
)
from smplkit._generated.logging.client import AuthenticatedClient
from smplkit._generated.logging.api.loggers import (  # noqa: F401  (re-exported for tests + management)
    bulk_register_loggers,
    delete_logger,
    get_logger,
    list_loggers,
    update_logger,
)
from smplkit._generated.logging.api.log_groups import (  # noqa: F401  (re-exported)
    create_log_group,
    delete_log_group,
    get_log_group,
    list_log_groups,
    update_log_group,
)
from smplkit._generated.logging.models.log_group import LogGroup as GenLogGroup  # noqa: F401
from smplkit._generated.logging.models.log_group_resource import LogGroupResource  # noqa: F401
from smplkit._generated.logging.models.log_group_response import LogGroupResponse
from smplkit._generated.logging.models.logger import Logger as GenLogger  # noqa: F401
from smplkit._generated.logging.models.logger_resource import LoggerResource  # noqa: F401
from smplkit._generated.logging.models.logger_response import LoggerResponse
from smplkit.logging._levels import python_level_to_smpl, smpl_level_to_python
from smplkit.logging._normalize import normalize_logger_name
from smplkit.logging.adapters.base import LoggingAdapter
from smplkit.logging.helpers import (  # noqa: F401  (re-exported below)
    _build_log_group_body as _build_group_body,
    _build_logger_body,
    _extract_datetime,
    _extract_environments,
    _extract_sources,
    _loglevel_value,
    _make_environments,
    _make_group_environments,
    _str_to_log_level,
    _unset_to_none,
)
from smplkit.logging.models import (  # noqa: F401  (re-exported below)
    AsyncSmplLogGroup,
    AsyncSmplLogger,
    SmplLogGroup,
    SmplLogger,
)
from smplkit.logging._resolution import resolve_level
from smplkit.logging._sources import LoggerSource

if TYPE_CHECKING:
    from smplkit._metrics import _AsyncMetricsReporter, _MetricsReporter
    from smplkit.client import AsyncSmplClient, SmplClient
    from smplkit.management.client import AsyncSmplManagementClient, SmplManagementClient

logger = stdlib_logging.getLogger("smplkit")

_DEFAULT_LOGGING_BASE_URL = "https://logging.smplkit.com"


def _check_response_status(status_code: Any, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


def _exc_url(exc: Exception) -> str | None:
    try:
        return str(exc.request.url)  # type: ignore[attr-defined]
    except Exception:
        return None


def _maybe_reraise_network_error(exc: Exception, base_url: str | None = None) -> None:
    """Re-raise httpx exceptions as SDK exceptions if applicable."""
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


# ---------------------------------------------------------------------------
# Change event
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, kw_only=True)
class LoggerChangeEvent:
    """Describes a logger or group definition change.  Frozen — fields are set at construction."""

    id: str
    source: str
    deleted: bool = False


# ---------------------------------------------------------------------------
# Adapter auto-loading
# ---------------------------------------------------------------------------

_BUILTIN_ADAPTERS = [
    "smplkit.logging.adapters.stdlib_logging.StdlibLoggingAdapter",
    "smplkit.logging.adapters.loguru_adapter.LoguruAdapter",
]


def _auto_load_adapters() -> list[LoggingAdapter]:
    """Attempt to load all built-in adapters, skipping those whose dependencies are missing."""
    adapters: list[LoggingAdapter] = []
    for fqn in _BUILTIN_ADAPTERS:
        module_path, class_name = fqn.rsplit(".", 1)
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            adapters.append(cls())
            debug("lifecycle", f"Loaded logging adapter: {class_name}")
        except ImportError:
            debug("lifecycle", f"Skipped logging adapter {class_name} (dependency not installed)")
        except Exception:
            logger.warning("Failed to load logging adapter %s", class_name, exc_info=True)
    if not adapters:
        logger.warning("No logging framework detected. Runtime logging control requires a supported framework.")
    return adapters


# ---------------------------------------------------------------------------
# LoggingClient (sync)
# ---------------------------------------------------------------------------


class LoggingClient:
    """Synchronous logging runtime namespace.  Obtained via ``SmplClient(...).logging``.

    CRUD has moved to ``SmplManagementClient.loggers`` / ``.log_groups``
    (``mgmt.loggers.*`` / ``mgmt.log_groups.*``).
    """

    def __init__(
        self,
        parent: SmplClient,
        *,
        manage: SmplManagementClient,
        metrics: _MetricsReporter | None,
        logging_base_url: str = _DEFAULT_LOGGING_BASE_URL,
        app_base_url: str | None = None,
    ) -> None:
        self._parent = parent
        self._manage = manage
        self._metrics = metrics
        self._service = parent._service
        self._environment = parent._environment
        self._logging_base_url = logging_base_url
        self._logging_http = AuthenticatedClient(
            base_url=logging_base_url,
            token=parent._api_key,
        )
        self._connected = False
        self._name_map: dict[str, str] = {}  # original_name → normalized_id
        self._loggers_cache: dict[str, dict[str, Any]] = {}  # id → logger data
        self._groups_cache: dict[str, dict[str, Any]] = {}  # id → group data
        self._global_listeners: list[Callable[..., Any]] = []
        self._key_listeners: dict[str, list[Callable[..., Any]]] = {}
        self._adapters: list[LoggingAdapter] = []
        self._explicit_adapters = False
        self._ws_manager: Any = None

    # --- Adapter registration ---

    def register_adapter(self, adapter: LoggingAdapter) -> None:
        """Register a logging adapter. Must be called before start().

        If called at least once, auto-loading is disabled — only explicitly
        registered adapters are used.
        """
        if self._connected:
            raise RuntimeError("Cannot register adapters after start()")
        self._explicit_adapters = True
        self._adapters.append(adapter)

    # --- Runtime: start & change listeners ---

    def start(self) -> None:
        """Explicitly opt in to runtime logging control.

        Idempotent — safe to call multiple times.
        """
        debug("lifecycle", "LoggingClient.start() called")
        self._connect_internal()

    def on_change(self, fn_or_key: Callable[..., Any] | str | None = None) -> Any:
        """Register a change listener.

        Supports two forms:

        - ``@client.logging.on_change`` — registers a global listener.
        - ``@client.logging.on_change("sqlalchemy.engine")`` — registers a key-scoped listener.
        """
        if callable(fn_or_key):
            # @on_change (bare decorator)
            self._global_listeners.append(fn_or_key)
            return fn_or_key
        elif isinstance(fn_or_key, str):
            # @on_change("key")
            key = fn_or_key

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._key_listeners.setdefault(key, []).append(fn)
                return fn

            return decorator
        else:
            # @on_change() — called with parens but no args

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._global_listeners.append(fn)
                return fn

            return decorator

    # --- Prescriptive (connect-gated) ---

    def _connect_internal(self) -> None:
        """Called by ``SmplClient.connect()`` or :meth:`start`."""
        if self._connected:
            return

        # 0. Load adapters
        if not self._adapters:
            self._adapters = _auto_load_adapters()

        # 1. Discover existing loggers from all adapters
        mgmt_loggers = self._manage.loggers
        for adapter in self._adapters:
            try:
                existing = adapter.discover()
                debug("discovery", f"adapter {adapter.name!r} discovered {len(existing)} existing loggers")
                for name, explicit_level, effective_level in existing:
                    self._name_map[name] = normalize_logger_name(name)
                    mgmt_loggers.register(self._loggersource_for(name, explicit_level, effective_level))
            except Exception:
                logger.warning("Adapter %s discover() failed", adapter.name, exc_info=True)

        # 2. Install continuous discovery hooks
        for adapter in self._adapters:
            try:
                adapter.install_hook(self._on_new_logger)
            except Exception:
                logger.warning("Adapter %s install_hook() failed", adapter.name, exc_info=True)

        # 3. Flush initial batch
        try:
            self._manage.loggers.flush()
        except Exception as exc:
            logger.warning("Bulk logger registration failed: %s", exc)
            debug("registration", traceback.format_exc().strip())

        # 4-6. Fetch, resolve, apply
        try:
            self._fetch_and_apply(trigger="start()")
        except Exception as exc:
            logger.warning(
                "Failed to fetch/apply logging levels during connect (logging: %s): %s",
                self._logging_base_url,
                exc,
            )
            debug("resolution", traceback.format_exc().strip())

        # 7. Register WebSocket event handlers for real-time level updates
        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("logger_changed", self._handle_logger_changed)
        self._ws_manager.on("logger_deleted", self._handle_logger_deleted)
        self._ws_manager.on("group_changed", self._handle_group_changed)
        self._ws_manager.on("group_deleted", self._handle_group_deleted)
        self._ws_manager.on("loggers_changed", self._handle_loggers_changed)

        self._connected = True

    def _handle_logger_changed(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"logger_changed: fetching logger {key!r}")
        pre = dict(self._loggers_cache)
        try:
            response = get_logger.sync_detailed(key, client=self._logging_http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            logger.warning("Failed to fetch logger %r after WS event: %s", key, exc)
            debug("websocket", traceback.format_exc().strip())
            return
        if isinstance(response.parsed, LoggerResponse):
            r = response.parsed.data
            attrs = r.attributes
            lid = _unset_to_none(r.id) or key
            self._loggers_cache[lid] = {
                "level": _unset_to_none(attrs.level),
                "group": _unset_to_none(attrs.group),
                "managed": _unset_to_none(attrs.managed),
                "environments": _extract_environments(attrs.environments),
            }
        self._apply_levels()
        post = self._loggers_cache
        changed = [k for k in set(pre) | set(post) if pre.get(k) != post.get(k)]
        self._fire_change_listeners(changed, "websocket")

    def _handle_logger_deleted(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"logger_deleted: removing logger {key!r}")
        existed = key in self._loggers_cache
        self._loggers_cache.pop(key, None)
        self._apply_levels()
        if existed:
            self._fire_change_listeners([key], "websocket", deleted=True)

    def _handle_group_changed(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"group_changed: fetching group {key!r}")
        pre = dict(self._groups_cache)
        try:
            response = get_log_group.sync_detailed(key, client=self._logging_http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            logger.warning("Failed to fetch log group %r after WS event: %s", key, exc)
            debug("websocket", traceback.format_exc().strip())
            return
        if isinstance(response.parsed, LogGroupResponse):
            r = response.parsed.data
            attrs = r.attributes
            gid = _unset_to_none(r.id) or key
            self._groups_cache[gid] = {
                "level": _unset_to_none(attrs.level),
                "group": _unset_to_none(attrs.parent_id),
                "environments": _extract_environments(attrs.environments),
            }
        self._apply_levels()
        post = self._groups_cache
        changed = [k for k in set(pre) | set(post) if pre.get(k) != post.get(k)]
        self._fire_change_listeners(changed, "websocket")

    def _handle_group_deleted(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"group_deleted: removing group {key!r}")
        existed = key in self._groups_cache
        self._groups_cache.pop(key, None)
        self._apply_levels()
        if existed:
            self._fire_change_listeners([key], "websocket", deleted=True)

    def _handle_loggers_changed(self, data: dict) -> None:
        debug("websocket", "loggers_changed: full re-fetch")
        pre_loggers = dict(self._loggers_cache)
        pre_groups = dict(self._groups_cache)
        try:
            self._fetch_and_apply(trigger="loggers_changed WS event")
        except Exception as exc:
            logger.warning("Failed to re-fetch/apply logging levels after loggers_changed event: %s", exc)
            debug("websocket", traceback.format_exc().strip())
            return
        post_loggers = self._loggers_cache
        post_groups = self._groups_cache
        all_keys = (set(pre_loggers) | set(post_loggers)) | (set(pre_groups) | set(post_groups))
        changed = [
            k for k in all_keys if pre_loggers.get(k, pre_groups.get(k)) != post_loggers.get(k, post_groups.get(k))
        ]
        self._fire_change_listeners(changed, "websocket")

    def _fire_change_listeners(self, changed_keys: list[str], source: str, *, deleted: bool = False) -> None:
        if not changed_keys:
            return
        first_event = LoggerChangeEvent(id=changed_keys[0], source=source, deleted=deleted)
        for cb in self._global_listeners:
            try:
                cb(first_event)
            except Exception:
                logger.error("Exception in global logging on_change listener", exc_info=True)
        for k in changed_keys:
            event = LoggerChangeEvent(id=k, source=source, deleted=deleted)
            for cb in self._key_listeners.get(k, []):
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in key-scoped logging on_change listener", exc_info=True)

    def refresh(self) -> None:
        """Re-fetch all loggers and groups and update log levels."""
        debug("resolution", "refresh() called, triggering full resolution pass")
        self._fetch_and_apply(trigger="refresh()")

    def _close(self) -> None:
        """Called by ``SmplClient.close()``."""
        debug("lifecycle", "LoggingClient._close() called")
        for adapter in self._adapters:
            try:
                adapter.uninstall_hook()
            except Exception:
                logger.warning("Adapter %s uninstall_hook() failed", adapter.name, exc_info=True)
        if self._ws_manager is not None:
            self._ws_manager.off("logger_changed", self._handle_logger_changed)
            self._ws_manager.off("logger_deleted", self._handle_logger_deleted)
            self._ws_manager.off("group_changed", self._handle_group_changed)
            self._ws_manager.off("group_deleted", self._handle_group_deleted)
            self._ws_manager.off("loggers_changed", self._handle_loggers_changed)
            self._ws_manager = None

    # --- Internal ---

    def _loggersource_for(self, name: str, explicit_level: int | None, effective_level: int) -> LoggerSource:
        """Build a LoggerSource from an adapter's (name, explicit, effective) discovery tuple."""
        from smplkit import LogLevel

        return LoggerSource(
            name=name,
            resolved_level=LogLevel(python_level_to_smpl(effective_level)),
            level=LogLevel(python_level_to_smpl(explicit_level)) if explicit_level is not None else None,
            service=self._service,
            environment=self._environment,
        )

    def _on_new_logger(self, name: str, explicit_level: int | None, effective_level: int) -> None:
        """Callback from adapters when a new logger is created."""
        normalized = normalize_logger_name(name)
        debug("discovery", f"new logger intercepted via callback: {name!r} (normalized: {normalized!r})")
        self._name_map[name] = normalized
        mgmt_loggers = self._manage.loggers
        mgmt_loggers.register(self._loggersource_for(name, explicit_level, effective_level))
        debug(
            "registration",
            f"queued {name!r} for bulk registration (buffer size: {mgmt_loggers.pending_count})",
        )

        # If connected, try to apply level from cache
        if self._connected and normalized in self._loggers_cache:
            entry = self._loggers_cache[normalized]
            if entry.get("managed"):
                debug("resolution", f"applying immediate level for newly discovered managed logger {name!r}")
                resolved = resolve_level(normalized, self._environment, self._loggers_cache, self._groups_cache)
                python_level = smpl_level_to_python(resolved)
                for adapter in self._adapters:
                    try:
                        adapter.apply_level(name, python_level)
                    except Exception:
                        logger.warning("Adapter %s apply_level() failed for %s", adapter.name, name, exc_info=True)

    def _fetch_and_apply(self, trigger: str = "unknown") -> None:
        """Fetch all loggers/groups, resolve levels, apply to runtime."""
        debug("resolution", f"full resolution pass starting (trigger: {trigger})")
        # Fetch loggers
        debug("api", "GET /api/v1/loggers")
        try:
            response = list_loggers.sync_detailed(client=self._logging_http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._logging_base_url)
            raise
        loggers_data: dict[str, dict[str, Any]] = {}
        if response.parsed is not None and hasattr(response.parsed, "data"):
            for r in response.parsed.data:
                attrs = r.attributes
                lid = _unset_to_none(r.id) or ""
                loggers_data[lid] = {
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.group),
                    "managed": _unset_to_none(attrs.managed),
                    "environments": _extract_environments(attrs.environments),
                }
        debug("api", f"GET /api/v1/loggers -> {response.status_code.value} ({len(loggers_data)} loggers)")

        # Fetch groups
        debug("api", "GET /api/v1/log-groups")
        try:
            grp_response = list_log_groups.sync_detailed(client=self._logging_http)
            _check_response_status(grp_response.status_code, grp_response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._logging_base_url)
            raise
        groups_data: dict[str, dict[str, Any]] = {}
        if grp_response.parsed is not None and hasattr(grp_response.parsed, "data"):
            for r in grp_response.parsed.data:
                attrs = r.attributes
                gid = _unset_to_none(r.id) or ""
                groups_data[gid] = {
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.parent_id),
                    "environments": _extract_environments(attrs.environments),
                }
        debug("api", f"GET /api/v1/log-groups -> {grp_response.status_code.value} ({len(groups_data)} groups)")

        self._loggers_cache = loggers_data
        self._groups_cache = groups_data

        # Resolve and apply
        self._apply_levels()

    def _apply_levels(self) -> None:
        """Apply resolved levels to all managed, locally-present loggers."""
        debug("resolution", f"running full resolution pass for {len(self._name_map)} local loggers")
        for original_name, normalized_id in self._name_map.items():
            entry = self._loggers_cache.get(normalized_id)
            if entry is None:
                continue
            if not entry.get("managed"):
                continue
            resolved = resolve_level(normalized_id, self._environment, self._loggers_cache, self._groups_cache)
            python_level = smpl_level_to_python(resolved)
            for adapter in self._adapters:
                try:
                    adapter.apply_level(original_name, python_level)
                except Exception:
                    logger.warning("Adapter %s apply_level() failed for %s", adapter.name, original_name, exc_info=True)
            metrics = self._metrics
            if metrics is not None:
                metrics.record("logging.level_changes", unit="changes", dimensions={"logger": normalized_id})


# ---------------------------------------------------------------------------
# AsyncLoggingClient
# ---------------------------------------------------------------------------


class AsyncLoggingClient:
    """Asynchronous logging runtime namespace.

    Obtained via ``AsyncSmplClient(...).logging``. CRUD has moved to
    ``AsyncSmplManagementClient.loggers`` / ``.log_groups``
    (``mgmt.loggers.*`` / ``mgmt.log_groups.*``).
    """

    def __init__(
        self,
        parent: AsyncSmplClient,
        *,
        manage: AsyncSmplManagementClient,
        metrics: _AsyncMetricsReporter | None,
        logging_base_url: str = _DEFAULT_LOGGING_BASE_URL,
        app_base_url: str | None = None,
    ) -> None:
        self._parent = parent
        self._manage = manage
        self._metrics = metrics
        self._service = parent._service
        self._environment = parent._environment
        self._logging_base_url = logging_base_url
        self._logging_http = AuthenticatedClient(
            base_url=logging_base_url,
            token=parent._api_key,
        )
        self._connected = False
        self._name_map: dict[str, str] = {}
        self._loggers_cache: dict[str, dict[str, Any]] = {}
        self._groups_cache: dict[str, dict[str, Any]] = {}
        self._global_listeners: list[Callable[..., Any]] = []
        self._key_listeners: dict[str, list[Callable[..., Any]]] = {}
        self._adapters: list[LoggingAdapter] = []
        self._explicit_adapters = False
        self._ws_manager: Any = None

    # --- Adapter registration ---

    def register_adapter(self, adapter: LoggingAdapter) -> None:
        """Register a logging adapter. Must be called before start().

        If called at least once, auto-loading is disabled — only explicitly
        registered adapters are used.
        """
        if self._connected:
            raise RuntimeError("Cannot register adapters after start()")
        self._explicit_adapters = True
        self._adapters.append(adapter)

    # --- Runtime: start & change listeners ---

    async def start(self) -> None:
        """Explicitly opt in to runtime logging control.

        Idempotent — safe to call multiple times.
        """
        debug("lifecycle", "AsyncLoggingClient.start() called")
        await self._connect_internal()

    def on_change(self, fn_or_key: Callable[..., Any] | str | None = None) -> Any:
        """Register a change listener.

        Supports two forms:

        - ``@client.logging.on_change`` — registers a global listener.
        - ``@client.logging.on_change("sqlalchemy.engine")`` — registers a key-scoped listener.
        """
        if callable(fn_or_key):
            # @on_change (bare decorator)
            self._global_listeners.append(fn_or_key)
            return fn_or_key
        elif isinstance(fn_or_key, str):
            # @on_change("key")
            key = fn_or_key

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._key_listeners.setdefault(key, []).append(fn)
                return fn

            return decorator
        else:
            # @on_change() — called with parens but no args

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._global_listeners.append(fn)
                return fn

            return decorator

    # --- Prescriptive (connect-gated) ---

    async def _connect_internal(self) -> None:
        """Called by ``AsyncSmplClient.connect()`` or :meth:`start`."""
        if self._connected:
            return

        # 0. Load adapters
        if not self._adapters:
            self._adapters = _auto_load_adapters()

        # 1. Discover existing loggers from all adapters
        mgmt_loggers = self._manage.loggers
        for adapter in self._adapters:
            try:
                existing = adapter.discover()
                debug("discovery", f"adapter {adapter.name!r} discovered {len(existing)} existing loggers")
                for name, explicit_level, effective_level in existing:
                    self._name_map[name] = normalize_logger_name(name)
                    mgmt_loggers.register(self._loggersource_for(name, explicit_level, effective_level))
            except Exception:
                logger.warning("Adapter %s discover() failed", adapter.name, exc_info=True)

        # 2. Install continuous discovery hooks
        for adapter in self._adapters:
            try:
                adapter.install_hook(self._on_new_logger)
            except Exception:
                logger.warning("Adapter %s install_hook() failed", adapter.name, exc_info=True)

        await self._flush_bulk_async()

        try:
            await self._fetch_and_apply(trigger="start()")
        except Exception as exc:
            logger.warning(
                "Failed to fetch/apply logging levels during connect (logging: %s): %s",
                self._logging_base_url,
                exc,
            )
            debug("resolution", traceback.format_exc().strip())

        # Register WebSocket event handlers for real-time level updates
        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("logger_changed", self._handle_logger_changed)
        self._ws_manager.on("logger_deleted", self._handle_logger_deleted)
        self._ws_manager.on("group_changed", self._handle_group_changed)
        self._ws_manager.on("group_deleted", self._handle_group_deleted)
        self._ws_manager.on("loggers_changed", self._handle_loggers_changed)

        self._connected = True

    def _handle_logger_changed(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"logger_changed: fetching logger {key!r}")
        self._run_ws_handler(self._fetch_logger_and_apply, key)

    def _handle_logger_deleted(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"logger_deleted: removing logger {key!r}")
        existed = key in self._loggers_cache
        self._loggers_cache.pop(key, None)
        # Re-apply synchronously since we already have all cached data
        import asyncio as _asyncio

        def _run() -> None:
            try:
                _asyncio.run(self._async_apply_and_fire_deleted(key, existed))
            except Exception as exc:
                logger.warning("Failed to apply levels after logger_deleted event: %s", exc)

        threading.Thread(target=_run, name="smplkit-logging-ws-deleted", daemon=True).start()

    def _handle_group_changed(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"group_changed: fetching group {key!r}")
        self._run_ws_handler(self._fetch_group_and_apply, key)

    def _handle_group_deleted(self, data: dict) -> None:
        key = data.get("id", "")
        debug("websocket", f"group_deleted: removing group {key!r}")
        existed = key in self._groups_cache
        self._groups_cache.pop(key, None)
        import asyncio as _asyncio

        def _run() -> None:
            try:
                _asyncio.run(self._async_apply_and_fire_deleted(key, existed))
            except Exception as exc:
                logger.warning("Failed to apply levels after group_deleted event: %s", exc)

        threading.Thread(target=_run, name="smplkit-logging-ws-deleted", daemon=True).start()

    def _handle_loggers_changed(self, data: dict) -> None:
        debug("websocket", "loggers_changed: full re-fetch")
        api_key = self._parent._api_key
        logging_base_url = self._logging_base_url
        pre_loggers = dict(self._loggers_cache)
        pre_groups = dict(self._groups_cache)

        async def _do_refresh() -> None:
            http = AuthenticatedClient(base_url=logging_base_url, token=api_key)
            try:
                await self._fetch_and_apply(trigger="loggers_changed WS event", http_client=http)
            finally:
                ac = http._async_client
                if ac is not None:
                    await ac.aclose()
            post_loggers = self._loggers_cache
            post_groups = self._groups_cache
            all_keys = (set(pre_loggers) | set(post_loggers)) | (set(pre_groups) | set(post_groups))
            changed = [
                k for k in all_keys if pre_loggers.get(k, pre_groups.get(k)) != post_loggers.get(k, post_groups.get(k))
            ]
            self._fire_change_listeners(changed, "websocket")

        import asyncio as _asyncio

        def _run() -> None:
            try:
                _asyncio.run(_do_refresh())
            except Exception as exc:
                logger.warning("Failed to re-fetch/apply logging levels after loggers_changed event: %s", exc)
                debug("websocket", traceback.format_exc().strip())

        threading.Thread(target=_run, name="smplkit-logging-ws-refresh", daemon=True).start()

    def _run_ws_handler(self, coro_fn: Any, key: str) -> None:
        """Run an async handler in a fresh event loop (WS thread pattern)."""
        api_key = self._parent._api_key
        logging_base_url = self._logging_base_url
        import asyncio as _asyncio

        async def _run_async() -> None:
            http = AuthenticatedClient(base_url=logging_base_url, token=api_key)
            try:
                await coro_fn(key, http)
            finally:
                ac = http._async_client
                if ac is not None:
                    await ac.aclose()

        def _run() -> None:
            try:
                _asyncio.run(_run_async())
            except Exception as exc:
                logger.warning("Failed to handle WS event for %r: %s", key, exc)
                debug("websocket", traceback.format_exc().strip())

        threading.Thread(target=_run, name="smplkit-logging-ws-handler", daemon=True).start()

    async def _fetch_logger_and_apply(self, key: str, http: AuthenticatedClient) -> None:
        pre = dict(self._loggers_cache)
        try:
            response = await get_logger.asyncio_detailed(key, client=http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            logger.warning("Failed to fetch logger %r after WS event: %s", key, exc)
            return
        if isinstance(response.parsed, LoggerResponse):
            r = response.parsed.data
            attrs = r.attributes
            lid = _unset_to_none(r.id) or key
            self._loggers_cache[lid] = {
                "level": _unset_to_none(attrs.level),
                "group": _unset_to_none(attrs.group),
                "managed": _unset_to_none(attrs.managed),
                "environments": _extract_environments(attrs.environments),
            }
        self._apply_levels()
        post = self._loggers_cache
        changed = [k for k in set(pre) | set(post) if pre.get(k) != post.get(k)]
        self._fire_change_listeners(changed, "websocket")

    async def _fetch_group_and_apply(self, key: str, http: AuthenticatedClient) -> None:
        pre = dict(self._groups_cache)
        try:
            response = await get_log_group.asyncio_detailed(key, client=http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            logger.warning("Failed to fetch log group %r after WS event: %s", key, exc)
            return
        if isinstance(response.parsed, LogGroupResponse):
            r = response.parsed.data
            attrs = r.attributes
            gid = _unset_to_none(r.id) or key
            self._groups_cache[gid] = {
                "level": _unset_to_none(attrs.level),
                "group": _unset_to_none(attrs.parent_id),
                "environments": _extract_environments(attrs.environments),
            }
        self._apply_levels()
        post = self._groups_cache
        changed = [k for k in set(pre) | set(post) if pre.get(k) != post.get(k)]
        self._fire_change_listeners(changed, "websocket")

    async def _async_apply_and_fire_deleted(self, key: str, existed: bool) -> None:
        self._apply_levels()
        if existed:
            self._fire_change_listeners([key], "websocket", deleted=True)

    def _fire_change_listeners(self, changed_keys: list[str], source: str, *, deleted: bool = False) -> None:
        if not changed_keys:
            return
        first_event = LoggerChangeEvent(id=changed_keys[0], source=source, deleted=deleted)
        for cb in self._global_listeners:
            try:
                cb(first_event)
            except Exception:
                logger.error("Exception in global logging on_change listener", exc_info=True)
        for k in changed_keys:
            event = LoggerChangeEvent(id=k, source=source, deleted=deleted)
            for cb in self._key_listeners.get(k, []):
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in key-scoped logging on_change listener", exc_info=True)

    async def refresh(self) -> None:
        """Re-fetch all loggers and groups and update log levels."""
        debug("resolution", "refresh() called, triggering full resolution pass")
        await self._fetch_and_apply(trigger="refresh()")

    def _close(self) -> None:
        """Called by ``AsyncSmplClient.close()``."""
        debug("lifecycle", "AsyncLoggingClient._close() called")
        for adapter in self._adapters:
            try:
                adapter.uninstall_hook()
            except Exception:
                logger.warning("Adapter %s uninstall_hook() failed", adapter.name, exc_info=True)
        if self._ws_manager is not None:
            self._ws_manager.off("logger_changed", self._handle_logger_changed)
            self._ws_manager.off("logger_deleted", self._handle_logger_deleted)
            self._ws_manager.off("group_changed", self._handle_group_changed)
            self._ws_manager.off("group_deleted", self._handle_group_deleted)
            self._ws_manager.off("loggers_changed", self._handle_loggers_changed)
            self._ws_manager = None

    # --- Internal ---

    def _loggersource_for(self, name: str, explicit_level: int | None, effective_level: int) -> LoggerSource:
        """Build a LoggerSource from an adapter's (name, explicit, effective) discovery tuple."""
        from smplkit import LogLevel

        return LoggerSource(
            name=name,
            resolved_level=LogLevel(python_level_to_smpl(effective_level)),
            level=LogLevel(python_level_to_smpl(explicit_level)) if explicit_level is not None else None,
            service=self._service,
            environment=self._environment,
        )

    def _on_new_logger(self, name: str, explicit_level: int | None, effective_level: int) -> None:
        """Callback from adapters when a new logger is created."""
        normalized = normalize_logger_name(name)
        debug("discovery", f"new logger intercepted via callback: {name!r} (normalized: {normalized!r})")
        self._name_map[name] = normalized
        mgmt_loggers = self._manage.loggers
        mgmt_loggers.register(self._loggersource_for(name, explicit_level, effective_level))
        debug(
            "registration",
            f"queued {name!r} for bulk registration (buffer size: {mgmt_loggers.pending_count})",
        )

        if self._connected and normalized in self._loggers_cache:
            entry = self._loggers_cache[normalized]
            if entry.get("managed"):
                debug("resolution", f"applying immediate level for newly discovered managed logger {name!r}")
                resolved = resolve_level(normalized, self._environment, self._loggers_cache, self._groups_cache)
                python_level = smpl_level_to_python(resolved)
                for adapter in self._adapters:
                    try:
                        adapter.apply_level(name, python_level)
                    except Exception:
                        logger.warning("Adapter %s apply_level() failed for %s", adapter.name, name, exc_info=True)

    async def _flush_bulk_async(self) -> None:
        """Flush the registration buffer (delegates to mgmt.loggers)."""
        try:
            await self._manage.loggers.flush()
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if status is not None:
                logger.warning("Bulk logger registration failed: HTTP %s: %s", status, exc)
            else:
                logger.warning("Bulk logger registration failed (logging: %s): %s", self._logging_base_url, exc)
            debug("registration", traceback.format_exc().strip())

    async def _fetch_and_apply(self, trigger: str = "unknown", http_client: AuthenticatedClient | None = None) -> None:
        """Fetch all loggers/groups, resolve levels, apply to runtime.

        ``http_client``, when supplied, is used instead of ``self._logging_http``.
        Pass a fresh client when calling from a temporary event loop (e.g. the
        WS-event refresh thread) to prevent cross-loop httpx transport reuse.
        """
        http = http_client if http_client is not None else self._logging_http
        debug("resolution", f"full resolution pass starting (trigger: {trigger})")
        debug("api", "GET /api/v1/loggers")
        try:
            response = await list_loggers.asyncio_detailed(client=http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc, http._base_url)
            raise
        loggers_data: dict[str, dict[str, Any]] = {}
        if response.parsed is not None and hasattr(response.parsed, "data"):
            for r in response.parsed.data:
                attrs = r.attributes
                lid = _unset_to_none(r.id) or ""
                loggers_data[lid] = {
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.group),
                    "managed": _unset_to_none(attrs.managed),
                    "environments": _extract_environments(attrs.environments),
                }
        debug("api", f"GET /api/v1/loggers -> {response.status_code.value} ({len(loggers_data)} loggers)")

        debug("api", "GET /api/v1/log-groups")
        try:
            grp_response = await list_log_groups.asyncio_detailed(client=http)
            _check_response_status(grp_response.status_code, grp_response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc, http._base_url)
            raise
        groups_data: dict[str, dict[str, Any]] = {}
        if grp_response.parsed is not None and hasattr(grp_response.parsed, "data"):
            for r in grp_response.parsed.data:
                attrs = r.attributes
                gid = _unset_to_none(r.id) or ""
                groups_data[gid] = {
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.parent_id),
                    "environments": _extract_environments(attrs.environments),
                }
        debug("api", f"GET /api/v1/log-groups -> {grp_response.status_code.value} ({len(groups_data)} groups)")

        self._loggers_cache = loggers_data
        self._groups_cache = groups_data
        self._apply_levels()

    def _apply_levels(self) -> None:
        """Apply resolved levels to all managed, locally-present loggers."""
        debug("resolution", f"running full resolution pass for {len(self._name_map)} local loggers")
        for original_name, normalized_id in self._name_map.items():
            entry = self._loggers_cache.get(normalized_id)
            if entry is None:
                continue
            if not entry.get("managed"):
                continue
            resolved = resolve_level(normalized_id, self._environment, self._loggers_cache, self._groups_cache)
            python_level = smpl_level_to_python(resolved)
            for adapter in self._adapters:
                try:
                    adapter.apply_level(original_name, python_level)
                except Exception:
                    logger.warning("Adapter %s apply_level() failed for %s", adapter.name, original_name, exc_info=True)
            metrics = self._metrics
            if metrics is not None:
                metrics.record("logging.level_changes", unit="changes", dimensions={"logger": normalized_id})
