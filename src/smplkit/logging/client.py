"""LoggingClient and AsyncLoggingClient — management and prescriptive operations for logging."""

from __future__ import annotations

import importlib
import logging as stdlib_logging
import threading
import traceback
from collections import OrderedDict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Callable

from smplkit._debug import debug
from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
    _raise_for_status,
)
from smplkit._helpers import key_to_display_name
from smplkit._generated.logging.client import AuthenticatedClient
from smplkit._generated.logging.api.loggers import (
    bulk_register_loggers,
    delete_logger,
    get_logger,
    list_loggers,
    update_logger,
)
from smplkit._generated.logging.api.log_groups import (
    create_log_group,
    delete_log_group,
    get_log_group,
    list_log_groups,
    update_log_group,
)
from smplkit._generated.logging.models.logger import Logger as GenLogger
from smplkit._generated.logging.models.log_group import LogGroup as GenLogGroup
from smplkit._generated.logging.models.logger_resource import LoggerResource
from smplkit._generated.logging.models.log_group_resource import LogGroupResource
from smplkit._generated.logging.models.logger_response import LoggerResponse
from smplkit._generated.logging.models.log_group_response import LogGroupResponse
from smplkit._generated.logging.models.logger_bulk_item import LoggerBulkItem
from smplkit._generated.logging.models.logger_bulk_request import LoggerBulkRequest
from smplkit._generated.logging.models.logger_environments_type_0 import LoggerEnvironmentsType0
from smplkit._generated.logging.models.log_group_environments_type_0 import LogGroupEnvironmentsType0
from smplkit.logging._levels import python_level_to_smpl, smpl_level_to_python
from smplkit.logging._normalize import normalize_logger_name
from smplkit.logging.adapters.base import LoggingAdapter
from smplkit.logging._resolution import resolve_level

if TYPE_CHECKING:
    from smplkit import LogLevel
    from smplkit.client import AsyncSmplClient, SmplClient

logger = stdlib_logging.getLogger("smplkit")

_DEFAULT_LOGGING_BASE_URL = "https://logging.smplkit.com"
_BULK_FLUSH_THRESHOLD = 50
_BULK_FLUSH_INTERVAL = 5.0  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unset_to_none(value: Any) -> Any:
    """Convert Unset sentinels to None."""
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _extract_datetime(value: Any) -> Any:
    """Pass through datetime objects, return None for Unset/None."""
    if value is None:
        return None
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _extract_environments(environments: Any) -> dict[str, Any]:
    """Extract a plain dict from a generated environments object."""
    if environments is None:
        return {}
    type_name = type(environments).__name__
    if type_name == "Unset":
        return {}
    if isinstance(environments, (LoggerEnvironmentsType0, LogGroupEnvironmentsType0)):
        return dict(environments.additional_properties)
    if isinstance(environments, dict):
        return dict(environments)
    return {}


def _make_environments(environments: dict[str, Any] | None) -> LoggerEnvironmentsType0 | None:
    """Convert a plain dict to the generated LoggerEnvironmentsType0."""
    if environments is None:
        return None
    obj = LoggerEnvironmentsType0()
    obj.additional_properties = dict(environments)
    return obj


def _make_group_environments(environments: dict[str, Any] | None) -> LogGroupEnvironmentsType0 | None:
    """Convert a plain dict to the generated LogGroupEnvironmentsType0."""
    if environments is None:
        return None
    obj = LogGroupEnvironmentsType0()
    obj.additional_properties = dict(environments)
    return obj


def _extract_sources(sources: Any) -> list[dict[str, Any]]:
    """Extract sources list from generated model."""
    if sources is None:
        return []
    type_name = type(sources).__name__
    if type_name == "Unset":
        return []
    if isinstance(sources, list):
        result = []
        for item in sources:
            if hasattr(item, "additional_properties"):
                result.append(dict(item.additional_properties))
            elif isinstance(item, dict):
                result.append(item)
        return result
    return []


def _check_response_status(status_code: HTTPStatus, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


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


def _build_logger_body(
    *,
    logger_id: str | None = None,
    name: str,
    level: str | None = None,
    group: str | None = None,
    managed: bool | None = None,
    environments: dict[str, Any] | None = None,
) -> LoggerResponse:
    """Build a JSON:API request body for logger create/update."""
    attrs = GenLogger(
        name=name,
        level=level,
        group=group,
        managed=managed,
        environments=_make_environments(environments),
    )
    resource = LoggerResource(attributes=attrs, id=logger_id, type_="logger")
    return LoggerResponse(data=resource)


def _build_group_body(
    *,
    group_id: str | None = None,
    name: str,
    level: str | None = None,
    group: str | None = None,
    environments: dict[str, Any] | None = None,
) -> LogGroupResponse:
    """Build a JSON:API request body for log group create/update."""
    attrs = GenLogGroup(
        name=name,
        level=level,
        parent_id=group,
        environments=_make_group_environments(environments),
    )
    resource = LogGroupResource(attributes=attrs, id=group_id, type_="log_group")
    return LogGroupResponse(data=resource)


# ---------------------------------------------------------------------------
# Change event
# ---------------------------------------------------------------------------


class LoggerChangeEvent:
    """Describes a logger or group definition change."""

    id: str
    source: str
    deleted: bool

    def __init__(self, *, id: str, source: str, deleted: bool = False) -> None:
        self.id = id
        self.source = source
        self.deleted = deleted

    def __repr__(self) -> str:
        return f"LoggerChangeEvent(id={self.id!r}, source={self.source!r}, deleted={self.deleted!r})"


# ---------------------------------------------------------------------------
# SDK model classes
# ---------------------------------------------------------------------------


class SmplLogger:
    """SDK model for a logger resource.

    Modify properties locally, then call :meth:`save` to persist.
    """

    id: str | None
    name: str
    level: str | None
    group: str | None
    managed: bool | None
    sources: list[dict[str, Any]]
    environments: dict[str, Any]
    created_at: Any
    updated_at: Any

    def __init__(
        self,
        client: LoggingClient | None = None,
        *,
        id: str | None = None,
        name: str,
        level: str | None = None,
        group: str | None = None,
        managed: bool | None = None,
        sources: list[dict[str, Any]] | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.name = name
        self.level = level
        self.group = group
        self.managed = managed
        self.sources = sources or []
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def save(self) -> None:
        """Persist this logger to the server (create or update)."""
        updated = self._client._save_logger(self)
        self._apply(updated)

    def setLevel(self, level: LogLevel) -> None:  # noqa: N802
        """Set the base log level."""
        self.level = level.value

    def clearLevel(self) -> None:  # noqa: N802
        """Remove the base log level."""
        self.level = None

    def setEnvironmentLevel(self, env: str, level: LogLevel) -> None:  # noqa: N802
        """Set the log level for a specific environment."""
        self.environments[env] = {"level": level.value}

    def clearEnvironmentLevel(self, env: str) -> None:  # noqa: N802
        """Remove the log level override for a specific environment."""
        self.environments.pop(env, None)

    def clearAllEnvironmentLevels(self) -> None:  # noqa: N802
        """Remove all environment-level overrides."""
        self.environments = {}

    def _apply(self, other: SmplLogger) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.managed = other.managed
        self.sources = other.sources
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"SmplLogger(id={self.id!r}, name={self.name!r})"


class AsyncSmplLogger:
    """Async SDK model for a logger resource.

    Modify properties locally, then call :meth:`save` to persist.
    """

    id: str | None
    name: str
    level: str | None
    group: str | None
    managed: bool | None
    sources: list[dict[str, Any]]
    environments: dict[str, Any]
    created_at: Any
    updated_at: Any

    def __init__(
        self,
        client: AsyncLoggingClient | None = None,
        *,
        id: str | None = None,
        name: str,
        level: str | None = None,
        group: str | None = None,
        managed: bool | None = None,
        sources: list[dict[str, Any]] | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.name = name
        self.level = level
        self.group = group
        self.managed = managed
        self.sources = sources or []
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    async def save(self) -> None:
        """Persist this logger to the server (create or update)."""
        updated = await self._client._save_logger(self)
        self._apply(updated)

    def setLevel(self, level: LogLevel) -> None:  # noqa: N802
        """Set the base log level."""
        self.level = level.value

    def clearLevel(self) -> None:  # noqa: N802
        """Remove the base log level."""
        self.level = None

    def setEnvironmentLevel(self, env: str, level: LogLevel) -> None:  # noqa: N802
        """Set the log level for a specific environment."""
        self.environments[env] = {"level": level.value}

    def clearEnvironmentLevel(self, env: str) -> None:  # noqa: N802
        """Remove the log level override for a specific environment."""
        self.environments.pop(env, None)

    def clearAllEnvironmentLevels(self) -> None:  # noqa: N802
        """Remove all environment-level overrides."""
        self.environments = {}

    def _apply(self, other: AsyncSmplLogger) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.managed = other.managed
        self.sources = other.sources
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"AsyncSmplLogger(id={self.id!r}, name={self.name!r})"


class SmplLogGroup:
    """SDK model for a log group resource.

    Modify properties locally, then call :meth:`save` to persist.
    """

    id: str | None
    name: str
    level: str | None
    group: str | None
    environments: dict[str, Any]
    created_at: Any
    updated_at: Any

    def __init__(
        self,
        client: LoggingClient | None = None,
        *,
        id: str | None = None,
        name: str,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.name = name
        self.level = level
        self.group = group
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def save(self) -> None:
        """Persist this group to the server (create or update)."""
        updated = self._client._save_group(self)
        self._apply(updated)

    def setLevel(self, level: LogLevel) -> None:  # noqa: N802
        """Set the base log level."""
        self.level = level.value

    def clearLevel(self) -> None:  # noqa: N802
        """Remove the base log level."""
        self.level = None

    def setEnvironmentLevel(self, env: str, level: LogLevel) -> None:  # noqa: N802
        """Set the log level for a specific environment."""
        self.environments[env] = {"level": level.value}

    def clearEnvironmentLevel(self, env: str) -> None:  # noqa: N802
        """Remove the log level override for a specific environment."""
        self.environments.pop(env, None)

    def clearAllEnvironmentLevels(self) -> None:  # noqa: N802
        """Remove all environment-level overrides."""
        self.environments = {}

    def _apply(self, other: SmplLogGroup) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"SmplLogGroup(id={self.id!r}, name={self.name!r})"


class AsyncSmplLogGroup:
    """Async SDK model for a log group resource.

    Modify properties locally, then call :meth:`save` to persist.
    """

    id: str | None
    name: str
    level: str | None
    group: str | None
    environments: dict[str, Any]
    created_at: Any
    updated_at: Any

    def __init__(
        self,
        client: AsyncLoggingClient | None = None,
        *,
        id: str | None = None,
        name: str,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.name = name
        self.level = level
        self.group = group
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    async def save(self) -> None:
        """Persist this group to the server (create or update)."""
        updated = await self._client._save_group(self)
        self._apply(updated)

    def setLevel(self, level: LogLevel) -> None:  # noqa: N802
        """Set the base log level."""
        self.level = level.value

    def clearLevel(self) -> None:  # noqa: N802
        """Remove the base log level."""
        self.level = None

    def setEnvironmentLevel(self, env: str, level: LogLevel) -> None:  # noqa: N802
        """Set the log level for a specific environment."""
        self.environments[env] = {"level": level.value}

    def clearEnvironmentLevel(self, env: str) -> None:  # noqa: N802
        """Remove the log level override for a specific environment."""
        self.environments.pop(env, None)

    def clearAllEnvironmentLevels(self) -> None:  # noqa: N802
        """Remove all environment-level overrides."""
        self.environments = {}

    def _apply(self, other: AsyncSmplLogGroup) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"AsyncSmplLogGroup(id={self.id!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Logger registration buffer
# ---------------------------------------------------------------------------


class _LoggerRegistrationBuffer:
    """Batches discovered loggers for bulk registration."""

    def __init__(self) -> None:
        self._seen: OrderedDict[str, str] = OrderedDict()  # normalized_id → resolved_level
        self._pending: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(
        self,
        normalized_id: str,
        smpl_level: str | None,
        smpl_resolved_level: str,
        service: str | None,
        environment: str | None,
    ) -> None:
        """Queue a logger for registration if not already seen.

        Args:
            normalized_id: Normalized logger name.
            smpl_level: Explicit smplkit level string, or None if the logger
                inherits its level from a parent.
            smpl_resolved_level: Effective smplkit level string (always non-None).
            service: Service name to include in the payload, or None.
            environment: Environment name to include in the payload, or None.
        """
        with self._lock:
            if normalized_id not in self._seen:
                self._seen[normalized_id] = smpl_resolved_level
                item: dict[str, Any] = {"id": normalized_id, "resolved_level": smpl_resolved_level}
                if smpl_level is not None:
                    item["level"] = smpl_level
                if service is not None:
                    item["service"] = service
                if environment is not None:
                    item["environment"] = environment
                self._pending.append(item)

    def drain(self) -> list[dict[str, Any]]:
        """Return and clear the pending batch."""
        with self._lock:
            batch = self._pending
            self._pending = []
            return batch

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)


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


class LoggingManagementClient:
    """Management (CRUD) operations for Smpl Logging.

    Obtained via ``SmplClient(...).logging.management``.
    """

    def __init__(self, parent: LoggingClient) -> None:
        self._parent = parent

    def new(self, id: str, *, name: str | None = None, managed: bool = False) -> SmplLogger:
        """Return a new unsaved :class:`SmplLogger`.

        Call :meth:`SmplLogger.save` to persist it.
        """
        return SmplLogger(
            self._parent,
            id=id,
            name=name if name is not None else key_to_display_name(id),
            managed=managed,
        )

    def list(self) -> list[SmplLogger]:
        """List all loggers."""
        try:
            response = list_loggers.sync_detailed(client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._parent._logger_resource_to_model(r) for r in response.parsed.data]

    def get(self, id: str) -> SmplLogger:
        """Get a logger by id."""
        try:
            response = get_logger.sync_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Logger with id {id!r} not found", status_code=404)
        return self._parent._logger_to_model(response.parsed)

    def delete(self, id: str) -> None:
        """Delete a logger by id."""
        try:
            response = delete_logger.sync_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)

    def new_group(self, id: str, *, name: str | None = None, group: str | None = None) -> SmplLogGroup:
        """Return a new unsaved :class:`SmplLogGroup`.

        Call :meth:`SmplLogGroup.save` to persist it.
        """
        return SmplLogGroup(
            self._parent,
            id=id,
            name=name if name is not None else key_to_display_name(id),
            group=group,
        )

    def list_groups(self) -> list[SmplLogGroup]:
        """List all log groups."""
        try:
            response = list_log_groups.sync_detailed(client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._parent._group_resource_to_model(r) for r in response.parsed.data]

    def get_group(self, id: str) -> SmplLogGroup:
        """Get a log group by id."""
        try:
            response = get_log_group.sync_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Log group with id {id!r} not found", status_code=404)
        return self._parent._group_to_model(response.parsed)

    def delete_group(self, id: str) -> None:
        """Delete a log group by id."""
        try:
            response = delete_log_group.sync_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)


class LoggingClient:
    """Synchronous logging namespace.  Obtained via ``SmplClient(...).logging``."""

    def __init__(
        self,
        parent: SmplClient,
        *,
        logging_base_url: str = _DEFAULT_LOGGING_BASE_URL,
        app_base_url: str | None = None,
    ) -> None:
        self._parent = parent
        self._logging_base_url = logging_base_url
        self._logging_http = AuthenticatedClient(
            base_url=logging_base_url,
            token=parent._api_key,
        )
        self._connected = False
        self._name_map: dict[str, str] = {}  # original_name → normalized_id
        self._buffer = _LoggerRegistrationBuffer()
        self._flush_timer: threading.Timer | None = None
        self._loggers_cache: dict[str, dict[str, Any]] = {}  # id → logger data
        self._groups_cache: dict[str, dict[str, Any]] = {}  # id → group data
        self._global_listeners: list[Callable[..., Any]] = []
        self._key_listeners: dict[str, list[Callable[..., Any]]] = {}
        self._adapters: list[LoggingAdapter] = []
        self._explicit_adapters = False
        self._ws_manager: Any = None
        self.management = LoggingManagementClient(self)

    def _save_logger(self, lg: SmplLogger) -> SmplLogger:
        """Create or update a logger. Called by SmplLogger.save(). PUT has upsert semantics."""
        body = _build_logger_body(
            logger_id=lg.id,
            name=lg.name,
            level=lg.level,
            managed=lg.managed,
            group=lg.group,
            environments=lg.environments if lg.environments else None,
        )
        try:
            response = update_logger.sync_detailed(lg.id, client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._logger_to_model(response.parsed)

    def _save_group(self, grp: SmplLogGroup) -> SmplLogGroup:
        """Create or update a group. Called by SmplLogGroup.save()."""
        body = _build_group_body(
            group_id=grp.id,
            name=grp.name,
            level=grp.level,
            group=grp.group,
            environments=grp.environments if grp.environments else None,
        )
        try:
            if grp.created_at is None:
                response = create_log_group.sync_detailed(client=self._logging_http, body=body)
            else:
                response = update_log_group.sync_detailed(grp.id, client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._group_to_model(response.parsed)

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
        for adapter in self._adapters:
            try:
                existing = adapter.discover()
                debug("discovery", f"adapter {adapter.name!r} discovered {len(existing)} existing loggers")
                for name, explicit_level, effective_level in existing:
                    normalized = normalize_logger_name(name)
                    self._name_map[name] = normalized
                    smpl_explicit = python_level_to_smpl(explicit_level) if explicit_level is not None else None
                    smpl_effective = python_level_to_smpl(effective_level)
                    self._buffer.add(
                        normalized, smpl_explicit, smpl_effective, self._parent._service, self._parent._environment
                    )
            except Exception:
                logger.warning("Adapter %s discover() failed", adapter.name, exc_info=True)

        # 2. Install continuous discovery hooks
        for adapter in self._adapters:
            try:
                adapter.install_hook(self._on_new_logger)
            except Exception:
                logger.warning("Adapter %s install_hook() failed", adapter.name, exc_info=True)

        # 3. Flush initial batch
        self._flush_bulk_sync()

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

        # 7. Start periodic flush timer
        self._schedule_flush()

        # 8. Register WebSocket event handlers for real-time level updates
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
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None

    # --- Internal ---

    def _on_new_logger(self, name: str, explicit_level: int | None, effective_level: int) -> None:
        """Callback from adapters when a new logger is created."""
        normalized = normalize_logger_name(name)
        debug("discovery", f"new logger intercepted via callback: {name!r} (normalized: {normalized!r})")
        self._name_map[name] = normalized
        smpl_explicit = python_level_to_smpl(explicit_level) if explicit_level is not None else None
        smpl_effective = python_level_to_smpl(effective_level)
        self._buffer.add(normalized, smpl_explicit, smpl_effective, self._parent._service, self._parent._environment)
        debug("registration", f"queued {name!r} for bulk registration (buffer size: {self._buffer.pending_count})")

        if self._buffer.pending_count >= _BULK_FLUSH_THRESHOLD:
            debug("registration", f"buffer threshold reached ({_BULK_FLUSH_THRESHOLD}), flushing")
            threading.Thread(target=self._flush_bulk_sync, daemon=True).start()

        # If connected, try to apply level from cache
        if self._connected and normalized in self._loggers_cache:
            entry = self._loggers_cache[normalized]
            if entry.get("managed"):
                debug("resolution", f"applying immediate level for newly discovered managed logger {name!r}")
                resolved = resolve_level(normalized, self._parent._environment, self._loggers_cache, self._groups_cache)
                python_level = smpl_level_to_python(resolved)
                for adapter in self._adapters:
                    try:
                        adapter.apply_level(name, python_level)
                    except Exception:
                        logger.warning("Adapter %s apply_level() failed for %s", adapter.name, name, exc_info=True)

    def _flush_bulk_sync(self) -> None:
        """Flush the registration buffer to the logging service."""
        batch = self._buffer.drain()
        if not batch:
            return
        debug("registration", f"flushing {len(batch)} loggers to POST /api/v1/loggers/bulk")
        items = [
            LoggerBulkItem(
                id=b["id"],
                level=b.get("level"),
                resolved_level=b["resolved_level"],
                service=b.get("service"),
                environment=b.get("environment"),
            )
            for b in batch
        ]
        body = LoggerBulkRequest(loggers=items)
        try:
            debug("api", f"POST /api/v1/loggers/bulk ({len(items)} loggers)")
            response = bulk_register_loggers.sync_detailed(client=self._logging_http, body=body)
            if response.status_code.value >= 300:
                detail = response.content[:500] if response.content else b""
                logger.warning(
                    "Bulk logger registration failed: HTTP %s: %s",
                    response.status_code.value,
                    detail.decode("utf-8", errors="replace"),
                )
                debug("api", f"POST /api/v1/loggers/bulk -> {response.status_code.value} (error)")
            else:
                debug(
                    "api",
                    f"POST /api/v1/loggers/bulk -> {response.status_code.value} ({len(items)} loggers registered)",
                )
                metrics = self._parent._metrics
                if metrics is not None:
                    metrics.record("logging.loggers_discovered", len(items), unit="loggers")
        except Exception as exc:
            logger.warning("Bulk logger registration failed (logging: %s): %s", self._logging_base_url, exc)
            debug("registration", traceback.format_exc().strip())

    def _schedule_flush(self) -> None:
        """Schedule the next periodic flush."""

        def _tick() -> None:
            self._flush_bulk_sync()
            if self._connected:
                self._schedule_flush()

        self._flush_timer = threading.Timer(_BULK_FLUSH_INTERVAL, _tick)
        self._flush_timer.daemon = True
        self._flush_timer.start()

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
            resolved = resolve_level(normalized_id, self._parent._environment, self._loggers_cache, self._groups_cache)
            python_level = smpl_level_to_python(resolved)
            for adapter in self._adapters:
                try:
                    adapter.apply_level(original_name, python_level)
                except Exception:
                    logger.warning("Adapter %s apply_level() failed for %s", adapter.name, original_name, exc_info=True)
            metrics = self._parent._metrics
            if metrics is not None:
                metrics.record("logging.level_changes", unit="changes", dimensions={"logger": normalized_id})

    # --- Model conversion ---

    def _logger_to_model(self, parsed: Any) -> SmplLogger:
        return self._logger_resource_to_model(parsed.data)

    def _logger_resource_to_model(self, resource: Any) -> SmplLogger:
        attrs = resource.attributes
        return SmplLogger(
            self,
            id=_unset_to_none(resource.id) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.group),
            managed=_unset_to_none(attrs.managed),
            sources=_extract_sources(getattr(attrs, "sources", None)),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )

    def _group_to_model(self, parsed: Any) -> SmplLogGroup:
        return self._group_resource_to_model(parsed.data)

    def _group_resource_to_model(self, resource: Any) -> SmplLogGroup:
        attrs = resource.attributes
        return SmplLogGroup(
            self,
            id=_unset_to_none(resource.id) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.parent_id),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


# ---------------------------------------------------------------------------
# AsyncLoggingClient
# ---------------------------------------------------------------------------


class AsyncLoggingManagementClient:
    """Management (CRUD) operations for Smpl Logging (async).

    Obtained via ``AsyncSmplClient(...).logging.management``.
    """

    def __init__(self, parent: AsyncLoggingClient) -> None:
        self._parent = parent

    def new(self, id: str, *, name: str | None = None, managed: bool = False) -> AsyncSmplLogger:
        """Return a new unsaved :class:`AsyncSmplLogger`.

        Call :meth:`AsyncSmplLogger.save` to persist it.
        """
        return AsyncSmplLogger(
            self._parent,
            id=id,
            name=name if name is not None else key_to_display_name(id),
            managed=managed,
        )

    async def list(self) -> list[AsyncSmplLogger]:
        """List all loggers."""
        try:
            response = await list_loggers.asyncio_detailed(client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._parent._logger_resource_to_model(r) for r in response.parsed.data]

    async def get(self, id: str) -> AsyncSmplLogger:
        """Get a logger by id."""
        try:
            response = await get_logger.asyncio_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Logger with id {id!r} not found", status_code=404)
        return self._parent._logger_to_model(response.parsed)

    async def delete(self, id: str) -> None:
        """Delete a logger by id."""
        try:
            response = await delete_logger.asyncio_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)

    def new_group(self, id: str, *, name: str | None = None, group: str | None = None) -> AsyncSmplLogGroup:
        """Return a new unsaved :class:`AsyncSmplLogGroup`.

        Call :meth:`AsyncSmplLogGroup.save` to persist it.
        """
        return AsyncSmplLogGroup(
            self._parent,
            id=id,
            name=name if name is not None else key_to_display_name(id),
            group=group,
        )

    async def list_groups(self) -> list[AsyncSmplLogGroup]:
        """List all log groups."""
        try:
            response = await list_log_groups.asyncio_detailed(client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._parent._group_resource_to_model(r) for r in response.parsed.data]

    async def get_group(self, id: str) -> AsyncSmplLogGroup:
        """Get a log group by id."""
        try:
            response = await get_log_group.asyncio_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Log group with id {id!r} not found", status_code=404)
        return self._parent._group_to_model(response.parsed)

    async def delete_group(self, id: str) -> None:
        """Delete a log group by id."""
        try:
            response = await delete_log_group.asyncio_detailed(id, client=self._parent._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._parent._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)


class AsyncLoggingClient:
    """Asynchronous logging namespace.  Obtained via ``AsyncSmplClient(...).logging``."""

    def __init__(
        self,
        parent: AsyncSmplClient,
        *,
        logging_base_url: str = _DEFAULT_LOGGING_BASE_URL,
        app_base_url: str | None = None,
    ) -> None:
        self._parent = parent
        self._logging_base_url = logging_base_url
        self._logging_http = AuthenticatedClient(
            base_url=logging_base_url,
            token=parent._api_key,
        )
        self._connected = False
        self._name_map: dict[str, str] = {}
        self._buffer = _LoggerRegistrationBuffer()
        self._flush_timer: threading.Timer | None = None
        self._loggers_cache: dict[str, dict[str, Any]] = {}
        self._groups_cache: dict[str, dict[str, Any]] = {}
        self._global_listeners: list[Callable[..., Any]] = []
        self._key_listeners: dict[str, list[Callable[..., Any]]] = {}
        self._adapters: list[LoggingAdapter] = []
        self._explicit_adapters = False
        self._ws_manager: Any = None
        self.management = AsyncLoggingManagementClient(self)

    async def _save_logger(self, lg: AsyncSmplLogger) -> AsyncSmplLogger:
        """Create or update a logger. Called by AsyncSmplLogger.save(). PUT has upsert semantics."""
        body = _build_logger_body(
            logger_id=lg.id,
            name=lg.name,
            level=lg.level,
            managed=lg.managed,
            group=lg.group,
            environments=lg.environments if lg.environments else None,
        )
        try:
            response = await update_logger.asyncio_detailed(lg.id, client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._logger_to_model(response.parsed)

    async def _save_group(self, grp: AsyncSmplLogGroup) -> AsyncSmplLogGroup:
        """Create or update a group. Called by AsyncSmplLogGroup.save()."""
        body = _build_group_body(
            group_id=grp.id,
            name=grp.name,
            level=grp.level,
            group=grp.group,
            environments=grp.environments if grp.environments else None,
        )
        try:
            if grp.created_at is None:
                response = await create_log_group.asyncio_detailed(client=self._logging_http, body=body)
            else:
                response = await update_log_group.asyncio_detailed(grp.id, client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._logging_base_url)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._group_to_model(response.parsed)

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
        for adapter in self._adapters:
            try:
                existing = adapter.discover()
                debug("discovery", f"adapter {adapter.name!r} discovered {len(existing)} existing loggers")
                for name, explicit_level, effective_level in existing:
                    normalized = normalize_logger_name(name)
                    self._name_map[name] = normalized
                    smpl_explicit = python_level_to_smpl(explicit_level) if explicit_level is not None else None
                    smpl_effective = python_level_to_smpl(effective_level)
                    self._buffer.add(
                        normalized, smpl_explicit, smpl_effective, self._parent._service, self._parent._environment
                    )
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

        self._schedule_flush()

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
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None

    # --- Internal ---

    def _on_new_logger(self, name: str, explicit_level: int | None, effective_level: int) -> None:
        """Callback from adapters when a new logger is created."""
        normalized = normalize_logger_name(name)
        debug("discovery", f"new logger intercepted via callback: {name!r} (normalized: {normalized!r})")
        self._name_map[name] = normalized
        smpl_explicit = python_level_to_smpl(explicit_level) if explicit_level is not None else None
        smpl_effective = python_level_to_smpl(effective_level)
        self._buffer.add(normalized, smpl_explicit, smpl_effective, self._parent._service, self._parent._environment)
        debug("registration", f"queued {name!r} for bulk registration (buffer size: {self._buffer.pending_count})")

        if self._connected and normalized in self._loggers_cache:
            entry = self._loggers_cache[normalized]
            if entry.get("managed"):
                debug("resolution", f"applying immediate level for newly discovered managed logger {name!r}")
                resolved = resolve_level(normalized, self._parent._environment, self._loggers_cache, self._groups_cache)
                python_level = smpl_level_to_python(resolved)
                for adapter in self._adapters:
                    try:
                        adapter.apply_level(name, python_level)
                    except Exception:
                        logger.warning("Adapter %s apply_level() failed for %s", adapter.name, name, exc_info=True)

    async def _flush_bulk_async(self) -> None:
        """Flush the registration buffer to the logging service."""
        batch = self._buffer.drain()
        if not batch:
            return
        debug("registration", f"flushing {len(batch)} loggers to POST /api/v1/loggers/bulk")
        items = [
            LoggerBulkItem(
                id=b["id"],
                level=b.get("level"),
                resolved_level=b["resolved_level"],
                service=b.get("service"),
                environment=b.get("environment"),
            )
            for b in batch
        ]
        body = LoggerBulkRequest(loggers=items)
        try:
            debug("api", f"POST /api/v1/loggers/bulk ({len(items)} loggers)")
            response = await bulk_register_loggers.asyncio_detailed(client=self._logging_http, body=body)
            if response.status_code.value >= 300:
                detail = response.content[:500] if response.content else b""
                logger.warning(
                    "Bulk logger registration failed: HTTP %s: %s",
                    response.status_code.value,
                    detail.decode("utf-8", errors="replace"),
                )
                debug("api", f"POST /api/v1/loggers/bulk -> {response.status_code.value} (error)")
            else:
                debug(
                    "api",
                    f"POST /api/v1/loggers/bulk -> {response.status_code.value} ({len(items)} loggers registered)",
                )
                metrics = self._parent._metrics
                if metrics is not None:
                    metrics.record("logging.loggers_discovered", len(items), unit="loggers")
        except Exception as exc:
            logger.warning("Bulk logger registration failed (logging: %s): %s", self._logging_base_url, exc)
            debug("registration", traceback.format_exc().strip())

    def _flush_bulk_sync(self) -> None:
        """Sync flush for the timer thread."""
        batch = self._buffer.drain()
        if not batch:
            return
        debug("registration", f"flushing {len(batch)} loggers to POST /api/v1/loggers/bulk (sync timer)")
        items = [
            LoggerBulkItem(
                id=b["id"],
                level=b.get("level"),
                resolved_level=b["resolved_level"],
                service=b.get("service"),
                environment=b.get("environment"),
            )
            for b in batch
        ]
        body = LoggerBulkRequest(loggers=items)
        try:
            debug("api", f"POST /api/v1/loggers/bulk ({len(items)} loggers)")
            response = bulk_register_loggers.sync_detailed(client=self._logging_http, body=body)
            if response.status_code.value >= 300:
                detail = response.content[:500] if response.content else b""
                logger.warning(
                    "Bulk logger registration failed: HTTP %s: %s",
                    response.status_code.value,
                    detail.decode("utf-8", errors="replace"),
                )
                debug("api", f"POST /api/v1/loggers/bulk -> {response.status_code.value} (error)")
            else:
                debug(
                    "api",
                    f"POST /api/v1/loggers/bulk -> {response.status_code.value} ({len(items)} loggers registered)",
                )
                metrics = self._parent._metrics
                if metrics is not None:
                    metrics.record("logging.loggers_discovered", len(items), unit="loggers")
        except Exception as exc:
            logger.warning("Bulk logger registration failed (logging: %s): %s", self._logging_base_url, exc)
            debug("registration", traceback.format_exc().strip())

    def _schedule_flush(self) -> None:
        """Schedule the next periodic flush."""

        def _tick() -> None:
            self._flush_bulk_sync()
            if self._connected:
                self._schedule_flush()

        self._flush_timer = threading.Timer(_BULK_FLUSH_INTERVAL, _tick)
        self._flush_timer.daemon = True
        self._flush_timer.start()

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
            resolved = resolve_level(normalized_id, self._parent._environment, self._loggers_cache, self._groups_cache)
            python_level = smpl_level_to_python(resolved)
            for adapter in self._adapters:
                try:
                    adapter.apply_level(original_name, python_level)
                except Exception:
                    logger.warning("Adapter %s apply_level() failed for %s", adapter.name, original_name, exc_info=True)
            metrics = self._parent._metrics
            if metrics is not None:
                metrics.record("logging.level_changes", unit="changes", dimensions={"logger": normalized_id})

    # --- Model conversion ---

    def _logger_to_model(self, parsed: Any) -> AsyncSmplLogger:
        return self._logger_resource_to_model(parsed.data)

    def _logger_resource_to_model(self, resource: Any) -> AsyncSmplLogger:
        attrs = resource.attributes
        return AsyncSmplLogger(
            self,
            id=_unset_to_none(resource.id) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.group),
            managed=_unset_to_none(attrs.managed),
            sources=_extract_sources(getattr(attrs, "sources", None)),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )

    def _group_to_model(self, parsed: Any) -> AsyncSmplLogGroup:
        return self._group_resource_to_model(parsed.data)

    def _group_resource_to_model(self, resource: Any) -> AsyncSmplLogGroup:
        attrs = resource.attributes
        return AsyncSmplLogGroup(
            self,
            id=_unset_to_none(resource.id) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.parent_id),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )
