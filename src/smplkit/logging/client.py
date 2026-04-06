"""LoggingClient and AsyncLoggingClient — management and prescriptive operations for logging."""

from __future__ import annotations

import logging as stdlib_logging
import threading
from collections import OrderedDict
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
    _raise_for_status,
)
from smplkit._generated.logging.client import AuthenticatedClient
from smplkit._generated.logging.api.loggers import (
    bulk_register_loggers,
    create_logger,
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
from smplkit._generated.logging.models.resource_logger import ResourceLogger
from smplkit._generated.logging.models.resource_log_group import ResourceLogGroup
from smplkit._generated.logging.models.response_logger import ResponseLogger
from smplkit._generated.logging.models.response_log_group import ResponseLogGroup
from smplkit._generated.logging.models.logger_bulk_item import LoggerBulkItem
from smplkit._generated.logging.models.logger_bulk_request import LoggerBulkRequest
from smplkit._generated.logging.models.logger_environments_type_0 import LoggerEnvironmentsType0
from smplkit._generated.logging.models.log_group_environments_type_0 import LogGroupEnvironmentsType0
from smplkit.logging._levels import python_level_to_smpl, smpl_level_to_python
from smplkit.logging._normalize import normalize_logger_name
from smplkit.logging._discovery import (
    discover_existing_loggers,
    install_discovery_patch,
    uninstall_discovery_patch,
)
from smplkit.logging._resolution import resolve_level

if TYPE_CHECKING:
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


def _maybe_reraise_network_error(exc: Exception) -> None:
    """Re-raise httpx exceptions as SDK exceptions if applicable."""
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        raise SmplTimeoutError(str(exc)) from exc
    if isinstance(exc, httpx.HTTPError):
        raise SmplConnectionError(str(exc)) from exc
    if isinstance(exc, (SmplNotFoundError, SmplConflictError, SmplValidationError)):
        raise exc


def _build_logger_body(
    *,
    logger_id: str | None = None,
    name: str,
    key: str | None = None,
    level: str | None = None,
    group: str | None = None,
    managed: bool | None = None,
    environments: dict[str, Any] | None = None,
) -> ResponseLogger:
    """Build a JSON:API request body for logger create/update."""
    attrs = GenLogger(
        name=name,
        key=key,
        level=level,
        group=group,
        managed=managed,
        environments=_make_environments(environments),
    )
    resource = ResourceLogger(attributes=attrs, id=logger_id, type_="logger")
    return ResponseLogger(data=resource)


def _build_group_body(
    *,
    group_id: str | None = None,
    name: str,
    key: str | None = None,
    level: str | None = None,
    group: str | None = None,
    environments: dict[str, Any] | None = None,
) -> ResponseLogGroup:
    """Build a JSON:API request body for log group create/update."""
    attrs = GenLogGroup(
        name=name,
        key=key,
        level=level,
        group=group,
        environments=_make_group_environments(environments),
    )
    resource = ResourceLogGroup(attributes=attrs, id=group_id, type_="log_group")
    return ResponseLogGroup(data=resource)


# ---------------------------------------------------------------------------
# SDK model classes
# ---------------------------------------------------------------------------


class SmplLogger:
    """SDK model for a logger resource.

    Supports GET-mutate-save: modify properties, then call :meth:`save`
    to PUT the full object back to the server.
    """

    def __init__(
        self,
        client: LoggingClient | None = None,
        *,
        id: str,
        key: str,
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
        self.key = key
        self.name = name
        self.level = level
        self.group = group
        self.managed = managed
        self.sources = sources or []
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def save(self) -> None:
        """PUT the full current state of this logger to the server."""
        updated = self._client._save_logger(self)
        self._apply(updated)

    def _apply(self, other: SmplLogger) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.key = other.key
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.managed = other.managed
        self.sources = other.sources
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"SmplLogger(id={self.id!r}, key={self.key!r}, name={self.name!r})"


class AsyncSmplLogger:
    """Async SDK model for a logger resource.

    Supports GET-mutate-save: modify properties, then call :meth:`save`
    to PUT the full object back to the server.
    """

    def __init__(
        self,
        client: AsyncLoggingClient | None = None,
        *,
        id: str,
        key: str,
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
        self.key = key
        self.name = name
        self.level = level
        self.group = group
        self.managed = managed
        self.sources = sources or []
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    async def save(self) -> None:
        """PUT the full current state of this logger to the server."""
        updated = await self._client._save_logger(self)
        self._apply(updated)

    def _apply(self, other: AsyncSmplLogger) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.key = other.key
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.managed = other.managed
        self.sources = other.sources
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"AsyncSmplLogger(id={self.id!r}, key={self.key!r}, name={self.name!r})"


class SmplLogGroup:
    """SDK model for a log group resource.

    Supports GET-mutate-save: modify properties, then call :meth:`save`
    to PUT the full object back to the server.
    """

    def __init__(
        self,
        client: LoggingClient | None = None,
        *,
        id: str,
        key: str,
        name: str,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.key = key
        self.name = name
        self.level = level
        self.group = group
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def save(self) -> None:
        """PUT the full current state of this group to the server."""
        updated = self._client._save_group(self)
        self._apply(updated)

    def _apply(self, other: SmplLogGroup) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.key = other.key
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"SmplLogGroup(id={self.id!r}, key={self.key!r}, name={self.name!r})"


class AsyncSmplLogGroup:
    """Async SDK model for a log group resource.

    Supports GET-mutate-save: modify properties, then call :meth:`save`
    to PUT the full object back to the server.
    """

    def __init__(
        self,
        client: AsyncLoggingClient | None = None,
        *,
        id: str,
        key: str,
        name: str,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
        created_at: Any = None,
        updated_at: Any = None,
    ) -> None:
        self._client = client
        self.id = id
        self.key = key
        self.name = name
        self.level = level
        self.group = group
        self.environments = environments or {}
        self.created_at = created_at
        self.updated_at = updated_at

    async def save(self) -> None:
        """PUT the full current state of this group to the server."""
        updated = await self._client._save_group(self)
        self._apply(updated)

    def _apply(self, other: AsyncSmplLogGroup) -> None:
        """Copy all properties from other into self."""
        self.id = other.id
        self.key = other.key
        self.name = other.name
        self.level = other.level
        self.group = other.group
        self.environments = other.environments
        self.created_at = other.created_at
        self.updated_at = other.updated_at

    def __repr__(self) -> str:
        return f"AsyncSmplLogGroup(id={self.id!r}, key={self.key!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Logger registration buffer
# ---------------------------------------------------------------------------


class _LoggerRegistrationBuffer:
    """Batches discovered loggers for bulk registration."""

    def __init__(self) -> None:
        self._seen: OrderedDict[str, str] = OrderedDict()  # normalized_key → smpl_level
        self._pending: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, normalized_key: str, smpl_level: str, service: str | None) -> None:
        """Queue a logger for registration if not already seen."""
        with self._lock:
            if normalized_key not in self._seen:
                self._seen[normalized_key] = smpl_level
                item: dict[str, Any] = {"key": normalized_key, "level": smpl_level}
                if service is not None:
                    item["service"] = service
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
# LoggingClient (sync)
# ---------------------------------------------------------------------------


class LoggingClient:
    """Synchronous logging namespace.  Obtained via ``SmplClient(...).logging``."""

    def __init__(self, parent: SmplClient) -> None:
        self._parent = parent
        self._logging_http = AuthenticatedClient(
            base_url=_DEFAULT_LOGGING_BASE_URL,
            token=parent._api_key,
        )
        self._connected = False
        self._name_map: dict[str, str] = {}  # original_name → normalized_key
        self._buffer = _LoggerRegistrationBuffer()
        self._flush_timer: threading.Timer | None = None
        self._loggers_cache: dict[str, dict[str, Any]] = {}  # key → logger data
        self._groups_cache: dict[str, dict[str, Any]] = {}  # id → group data

    # --- Management API: Loggers ---

    def create(
        self,
        key: str,
        *,
        name: str,
        managed: bool = False,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
    ) -> SmplLogger:
        """Create a logger."""
        body = _build_logger_body(
            name=name,
            key=key,
            level=level,
            group=group,
            managed=managed,
            environments=environments,
        )
        try:
            response = create_logger.sync_detailed(client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._logger_to_model(response.parsed)

    def list(self) -> list[SmplLogger]:
        """List all loggers."""
        try:
            response = list_loggers.sync_detailed(client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._logger_resource_to_model(r) for r in response.parsed.data]

    def get(self, logger_id: str) -> SmplLogger:
        """Get a logger by ID."""
        try:
            response = get_logger.sync_detailed(UUID(logger_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Logger {logger_id} not found")
        return self._logger_to_model(response.parsed)

    def _save_logger(self, lg: SmplLogger) -> SmplLogger:
        """PUT a logger's full state. Called by SmplLogger.save()."""
        body = _build_logger_body(
            logger_id=lg.id,
            name=lg.name,
            key=lg.key,
            level=lg.level,
            managed=lg.managed,
            group=lg.group,
            environments=lg.environments if lg.environments else None,
        )
        try:
            response = update_logger.sync_detailed(UUID(lg.id), client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._logger_to_model(response.parsed)

    def delete(self, logger_id: str) -> None:
        """Delete a logger."""
        try:
            response = delete_logger.sync_detailed(UUID(logger_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    # --- Management API: Log Groups ---

    def create_group(
        self,
        key: str,
        *,
        name: str,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
    ) -> SmplLogGroup:
        """Create a log group."""
        body = _build_group_body(name=name, key=key, level=level, group=group, environments=environments)
        try:
            response = create_log_group.sync_detailed(client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._group_to_model(response.parsed)

    def list_groups(self) -> list[SmplLogGroup]:
        """List all log groups."""
        try:
            response = list_log_groups.sync_detailed(client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._group_resource_to_model(r) for r in response.parsed.data]

    def get_group(self, group_id: str) -> SmplLogGroup:
        """Get a log group by ID."""
        try:
            response = get_log_group.sync_detailed(UUID(group_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Log group {group_id} not found")
        return self._group_to_model(response.parsed)

    def _save_group(self, grp: SmplLogGroup) -> SmplLogGroup:
        """PUT a group's full state. Called by SmplLogGroup.save()."""
        body = _build_group_body(
            group_id=grp.id,
            name=grp.name,
            key=grp.key,
            level=grp.level,
            group=grp.group,
            environments=grp.environments if grp.environments else None,
        )
        try:
            response = update_log_group.sync_detailed(UUID(grp.id), client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._group_to_model(response.parsed)

    def delete_group(self, group_id: str) -> None:
        """Delete a log group."""
        try:
            response = delete_log_group.sync_detailed(UUID(group_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    # --- Prescriptive (connect-gated) ---

    def _connect_internal(self) -> None:
        """Called by ``SmplClient.connect()``."""
        # 1. Discover existing loggers
        existing = discover_existing_loggers()
        for name, level in existing:
            normalized = normalize_logger_name(name)
            self._name_map[name] = normalized
            smpl_level = python_level_to_smpl(level)
            self._buffer.add(normalized, smpl_level, self._parent._service)

        # 2. Install continuous discovery
        install_discovery_patch(self._on_new_logger)

        # 3. Flush initial batch
        self._flush_bulk_sync()

        # 4-6. Fetch, resolve, apply
        try:
            self._fetch_and_apply()
        except Exception:
            logger.warning("Failed to fetch/apply logging levels during connect", exc_info=True)

        # 7. Start periodic flush timer
        self._schedule_flush()

        self._connected = True

    def refresh(self) -> None:
        """Re-fetch all loggers and groups, re-resolve, re-apply.

        Raises:
            SmplNotConnectedError: If called before connect.
        """
        if not self._connected:
            raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")
        self._fetch_and_apply()

    def _close(self) -> None:
        """Called by ``SmplClient.close()``."""
        uninstall_discovery_patch()
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None

    # --- Internal ---

    def _on_new_logger(self, name: str, level: int) -> None:
        """Callback from the monkey-patch when a new logger is created."""
        normalized = normalize_logger_name(name)
        self._name_map[name] = normalized
        smpl_level = python_level_to_smpl(level)
        self._buffer.add(normalized, smpl_level, self._parent._service)

        if self._buffer.pending_count >= _BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_bulk_sync, daemon=True).start()

        # If connected, try to apply level from cache
        if self._connected and normalized in self._loggers_cache:
            entry = self._loggers_cache[normalized]
            if entry.get("managed"):
                resolved = resolve_level(normalized, self._parent._environment, self._loggers_cache, self._groups_cache)
                stdlib_logging.getLogger(name).setLevel(smpl_level_to_python(resolved))

    def _flush_bulk_sync(self) -> None:
        """Flush the registration buffer to the logging service."""
        batch = self._buffer.drain()
        if not batch:
            return
        items = [LoggerBulkItem(key=b["key"], level=b["level"], service=b.get("service")) for b in batch]
        body = LoggerBulkRequest(loggers=items)
        try:
            bulk_register_loggers.sync_detailed(client=self._logging_http, body=body)
        except Exception:
            logger.debug("Bulk logger registration failed", exc_info=True)

    def _schedule_flush(self) -> None:
        """Schedule the next periodic flush."""

        def _tick() -> None:
            self._flush_bulk_sync()
            if self._connected:
                self._schedule_flush()

        self._flush_timer = threading.Timer(_BULK_FLUSH_INTERVAL, _tick)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _fetch_and_apply(self) -> None:
        """Fetch all loggers/groups, resolve levels, apply to runtime."""
        # Fetch loggers
        try:
            response = list_loggers.sync_detailed(client=self._logging_http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        loggers_data: dict[str, dict[str, Any]] = {}
        if response.parsed is not None and hasattr(response.parsed, "data"):
            for r in response.parsed.data:
                attrs = r.attributes
                key = _unset_to_none(attrs.key) or ""
                loggers_data[key] = {
                    "key": key,
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.group),
                    "managed": _unset_to_none(attrs.managed),
                    "environments": _extract_environments(attrs.environments),
                }

        # Fetch groups
        try:
            grp_response = list_log_groups.sync_detailed(client=self._logging_http)
            _check_response_status(grp_response.status_code, grp_response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        groups_data: dict[str, dict[str, Any]] = {}
        if grp_response.parsed is not None and hasattr(grp_response.parsed, "data"):
            for r in grp_response.parsed.data:
                attrs = r.attributes
                gid = _unset_to_none(r.id) or ""
                groups_data[gid] = {
                    "key": _unset_to_none(attrs.key) or "",
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.group),
                    "environments": _extract_environments(attrs.environments),
                }

        self._loggers_cache = loggers_data
        self._groups_cache = groups_data

        # Resolve and apply
        self._apply_levels()

    def _apply_levels(self) -> None:
        """Apply resolved levels to all managed, locally-present loggers."""
        for original_name, normalized_key in self._name_map.items():
            entry = self._loggers_cache.get(normalized_key)
            if entry is None:
                continue
            if not entry.get("managed"):
                continue
            resolved = resolve_level(normalized_key, self._parent._environment, self._loggers_cache, self._groups_cache)
            stdlib_logging.getLogger(original_name).setLevel(smpl_level_to_python(resolved))

    # --- Model conversion ---

    def _logger_to_model(self, parsed: Any) -> SmplLogger:
        return self._logger_resource_to_model(parsed.data)

    def _logger_resource_to_model(self, resource: Any) -> SmplLogger:
        attrs = resource.attributes
        return SmplLogger(
            self,
            id=_unset_to_none(resource.id) or "",
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.group),
            managed=_unset_to_none(attrs.managed),
            sources=_extract_sources(attrs.sources),
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
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.group),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


# ---------------------------------------------------------------------------
# AsyncLoggingClient
# ---------------------------------------------------------------------------


class AsyncLoggingClient:
    """Asynchronous logging namespace.  Obtained via ``AsyncSmplClient(...).logging``."""

    def __init__(self, parent: AsyncSmplClient) -> None:
        self._parent = parent
        self._logging_http = AuthenticatedClient(
            base_url=_DEFAULT_LOGGING_BASE_URL,
            token=parent._api_key,
        )
        self._connected = False
        self._name_map: dict[str, str] = {}
        self._buffer = _LoggerRegistrationBuffer()
        self._flush_timer: threading.Timer | None = None
        self._loggers_cache: dict[str, dict[str, Any]] = {}
        self._groups_cache: dict[str, dict[str, Any]] = {}

    # --- Management API: Loggers ---

    async def create(
        self,
        key: str,
        *,
        name: str,
        managed: bool = False,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
    ) -> AsyncSmplLogger:
        """Create a logger."""
        body = _build_logger_body(
            name=name,
            key=key,
            level=level,
            group=group,
            managed=managed,
            environments=environments,
        )
        try:
            response = await create_logger.asyncio_detailed(client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._logger_to_model(response.parsed)

    async def list(self) -> list[AsyncSmplLogger]:
        """List all loggers."""
        try:
            response = await list_loggers.asyncio_detailed(client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._logger_resource_to_model(r) for r in response.parsed.data]

    async def get(self, logger_id: str) -> AsyncSmplLogger:
        """Get a logger by ID."""
        try:
            response = await get_logger.asyncio_detailed(UUID(logger_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Logger {logger_id} not found")
        return self._logger_to_model(response.parsed)

    async def _save_logger(self, lg: AsyncSmplLogger) -> AsyncSmplLogger:
        """PUT a logger's full state. Called by AsyncSmplLogger.save()."""
        body = _build_logger_body(
            logger_id=lg.id,
            name=lg.name,
            key=lg.key,
            level=lg.level,
            managed=lg.managed,
            group=lg.group,
            environments=lg.environments if lg.environments else None,
        )
        try:
            response = await update_logger.asyncio_detailed(UUID(lg.id), client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._logger_to_model(response.parsed)

    async def delete(self, logger_id: str) -> None:
        """Delete a logger."""
        try:
            response = await delete_logger.asyncio_detailed(UUID(logger_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    # --- Management API: Log Groups ---

    async def create_group(
        self,
        key: str,
        *,
        name: str,
        level: str | None = None,
        group: str | None = None,
        environments: dict[str, Any] | None = None,
    ) -> AsyncSmplLogGroup:
        """Create a log group."""
        body = _build_group_body(name=name, key=key, level=level, group=group, environments=environments)
        try:
            response = await create_log_group.asyncio_detailed(client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._group_to_model(response.parsed)

    async def list_groups(self) -> list[AsyncSmplLogGroup]:
        """List all log groups."""
        try:
            response = await list_log_groups.asyncio_detailed(client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._group_resource_to_model(r) for r in response.parsed.data]

    async def get_group(self, group_id: str) -> AsyncSmplLogGroup:
        """Get a log group by ID."""
        try:
            response = await get_log_group.asyncio_detailed(UUID(group_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Log group {group_id} not found")
        return self._group_to_model(response.parsed)

    async def _save_group(self, grp: AsyncSmplLogGroup) -> AsyncSmplLogGroup:
        """PUT a group's full state. Called by AsyncSmplLogGroup.save()."""
        body = _build_group_body(
            group_id=grp.id,
            name=grp.name,
            key=grp.key,
            level=grp.level,
            group=grp.group,
            environments=grp.environments if grp.environments else None,
        )
        try:
            response = await update_log_group.asyncio_detailed(UUID(grp.id), client=self._logging_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            _raise_for_status(int(response.status_code), response.content)
            raise SmplValidationError(
                f"HTTP {int(response.status_code)}: unexpected response", status_code=int(response.status_code)
            )
        return self._group_to_model(response.parsed)

    async def delete_group(self, group_id: str) -> None:
        """Delete a log group."""
        try:
            response = await delete_log_group.asyncio_detailed(UUID(group_id), client=self._logging_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    # --- Prescriptive (connect-gated) ---

    async def _connect_internal(self) -> None:
        """Called by ``AsyncSmplClient.connect()``."""
        existing = discover_existing_loggers()
        for name, level in existing:
            normalized = normalize_logger_name(name)
            self._name_map[name] = normalized
            smpl_level = python_level_to_smpl(level)
            self._buffer.add(normalized, smpl_level, self._parent._service)

        install_discovery_patch(self._on_new_logger)

        await self._flush_bulk_async()

        try:
            await self._fetch_and_apply()
        except Exception:
            logger.warning("Failed to fetch/apply logging levels during connect", exc_info=True)

        self._schedule_flush()
        self._connected = True

    async def refresh(self) -> None:
        """Re-fetch all loggers and groups, re-resolve, re-apply."""
        if not self._connected:
            raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")
        await self._fetch_and_apply()

    def _close(self) -> None:
        """Called by ``AsyncSmplClient.close()``."""
        uninstall_discovery_patch()
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None

    # --- Internal ---

    def _on_new_logger(self, name: str, level: int) -> None:
        """Callback from the monkey-patch when a new logger is created."""
        normalized = normalize_logger_name(name)
        self._name_map[name] = normalized
        smpl_level = python_level_to_smpl(level)
        self._buffer.add(normalized, smpl_level, self._parent._service)

        if self._connected and normalized in self._loggers_cache:
            entry = self._loggers_cache[normalized]
            if entry.get("managed"):
                resolved = resolve_level(normalized, self._parent._environment, self._loggers_cache, self._groups_cache)
                stdlib_logging.getLogger(name).setLevel(smpl_level_to_python(resolved))

    async def _flush_bulk_async(self) -> None:
        """Flush the registration buffer to the logging service."""
        batch = self._buffer.drain()
        if not batch:
            return
        items = [LoggerBulkItem(key=b["key"], level=b["level"], service=b.get("service")) for b in batch]
        body = LoggerBulkRequest(loggers=items)
        try:
            await bulk_register_loggers.asyncio_detailed(client=self._logging_http, body=body)
        except Exception:
            logger.debug("Bulk logger registration failed", exc_info=True)

    def _flush_bulk_sync(self) -> None:
        """Sync flush for the timer thread."""
        batch = self._buffer.drain()
        if not batch:
            return
        items = [LoggerBulkItem(key=b["key"], level=b["level"], service=b.get("service")) for b in batch]
        body = LoggerBulkRequest(loggers=items)
        try:
            bulk_register_loggers.sync_detailed(client=self._logging_http, body=body)
        except Exception:
            logger.debug("Bulk logger registration failed", exc_info=True)

    def _schedule_flush(self) -> None:
        """Schedule the next periodic flush."""

        def _tick() -> None:
            self._flush_bulk_sync()
            if self._connected:
                self._schedule_flush()

        self._flush_timer = threading.Timer(_BULK_FLUSH_INTERVAL, _tick)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    async def _fetch_and_apply(self) -> None:
        """Fetch all loggers/groups, resolve levels, apply to runtime."""
        try:
            response = await list_loggers.asyncio_detailed(client=self._logging_http)
            _check_response_status(response.status_code, response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        loggers_data: dict[str, dict[str, Any]] = {}
        if response.parsed is not None and hasattr(response.parsed, "data"):
            for r in response.parsed.data:
                attrs = r.attributes
                key = _unset_to_none(attrs.key) or ""
                loggers_data[key] = {
                    "key": key,
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.group),
                    "managed": _unset_to_none(attrs.managed),
                    "environments": _extract_environments(attrs.environments),
                }

        try:
            grp_response = await list_log_groups.asyncio_detailed(client=self._logging_http)
            _check_response_status(grp_response.status_code, grp_response.content)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        groups_data: dict[str, dict[str, Any]] = {}
        if grp_response.parsed is not None and hasattr(grp_response.parsed, "data"):
            for r in grp_response.parsed.data:
                attrs = r.attributes
                gid = _unset_to_none(r.id) or ""
                groups_data[gid] = {
                    "key": _unset_to_none(attrs.key) or "",
                    "level": _unset_to_none(attrs.level),
                    "group": _unset_to_none(attrs.group),
                    "environments": _extract_environments(attrs.environments),
                }

        self._loggers_cache = loggers_data
        self._groups_cache = groups_data
        self._apply_levels()

    def _apply_levels(self) -> None:
        """Apply resolved levels to all managed, locally-present loggers."""
        for original_name, normalized_key in self._name_map.items():
            entry = self._loggers_cache.get(normalized_key)
            if entry is None:
                continue
            if not entry.get("managed"):
                continue
            resolved = resolve_level(normalized_key, self._parent._environment, self._loggers_cache, self._groups_cache)
            stdlib_logging.getLogger(original_name).setLevel(smpl_level_to_python(resolved))

    # --- Model conversion ---

    def _logger_to_model(self, parsed: Any) -> AsyncSmplLogger:
        return self._logger_resource_to_model(parsed.data)

    def _logger_resource_to_model(self, resource: Any) -> AsyncSmplLogger:
        attrs = resource.attributes
        return AsyncSmplLogger(
            self,
            id=_unset_to_none(resource.id) or "",
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.group),
            managed=_unset_to_none(attrs.managed),
            sources=_extract_sources(attrs.sources),
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
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            level=_unset_to_none(attrs.level),
            group=_unset_to_none(attrs.group),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )
