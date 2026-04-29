"""FlagsClient and AsyncFlagsClient — runtime evaluation for Smpl Flags.

Runtime: declare typed handles, evaluate via JSON Logic, cache
results, and react to live updates over a shared WebSocket. CRUD has
moved to :class:`smplkit.SmplManagementClient` (``mgmt.flags.*``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import traceback
from collections import OrderedDict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from smplkit._debug import debug
from smplkit._errors import (
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
    _raise_for_status,
)
from smplkit._generated.app.api.contexts import (
    bulk_register_contexts as gen_bulk_register_contexts,
)
from smplkit.management._buffer import _ContextRegistrationBuffer
from smplkit._generated.app.models.context_bulk_item import ContextBulkItem
from smplkit._generated.app.models.context_bulk_item_attributes import ContextBulkItemAttributes
from smplkit._generated.app.models.context_bulk_register import ContextBulkRegister
from smplkit._generated.flags.api.flags import (  # noqa: F401  (re-exported)
    bulk_register_flags,
    create_flag,
    delete_flag,
    get_flag,
    list_flags,
    update_flag,
)
from smplkit._generated.flags.models.flag_bulk_item import FlagBulkItem
from smplkit._generated.flags.models.flag_bulk_request import FlagBulkRequest
from smplkit._generated.flags.client import AuthenticatedClient
from smplkit.flags.helpers import _flag_dict_from_json
from smplkit.flags.models import (
    AsyncBooleanFlag,
    AsyncFlag,
    AsyncJsonFlag,
    AsyncNumberFlag,
    AsyncStringFlag,
    BooleanFlag,
    Flag,
    JsonFlag,
    NumberFlag,
    StringFlag,
)

if TYPE_CHECKING:
    from smplkit._ws import SharedWebSocket
    from smplkit.client import AsyncSmplClient, SmplClient
    from smplkit.flags.types import Context

logger = logging.getLogger("smplkit")
ws_logger = logging.getLogger("smplkit.flags.ws")

_DEFAULT_FLAGS_BASE_URL = "https://flags.smplkit.com"
_DEFAULT_APP_BASE_URL = "https://app.smplkit.com"
_CACHE_MAX_SIZE = 10_000
_CONTEXT_BATCH_FLUSH_SIZE = 100
_FLAG_BULK_FLUSH_THRESHOLD = 50
_FLAG_BULK_FLUSH_INTERVAL = 30.0  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_response_status(status_code: Any, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


def _exc_url(exc: Exception) -> str | None:
    """Extract URL from an httpx exception's associated request, if available."""
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
        raise SmplTimeoutError(msg) from exc
    if isinstance(exc, httpx.HTTPError):
        url = _exc_url(exc) or base_url
        msg = f"Cannot connect to {url}: {exc}" if url else f"Connection error: {exc}"
        raise SmplConnectionError(msg) from exc
    if isinstance(exc, (SmplNotFoundError, SmplValidationError)):
        raise exc


def _contexts_to_eval_dict(contexts: list[Context]) -> dict[str, Any]:
    """Convert a list of Context objects to the nested evaluation dict."""
    result: dict[str, Any] = {}
    for ctx in contexts:
        entry = {"key": ctx.key, **ctx.attributes}
        result[ctx.type] = entry
    return result


def _hash_context(eval_dict: dict[str, Any]) -> str:
    """Compute a stable hash for a context evaluation dict."""
    serialized = json.dumps(eval_dict, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Change event
# ---------------------------------------------------------------------------


class FlagChangeEvent:
    """Describes a flag definition change."""

    id: str
    source: str
    deleted: bool

    def __init__(self, *, id: str, source: str, deleted: bool = False) -> None:
        self.id = id
        self.source = source
        self.deleted = deleted

    def __repr__(self) -> str:
        return f"FlagChangeEvent(id={self.id!r}, source={self.source!r}, deleted={self.deleted!r})"


# ---------------------------------------------------------------------------
# Resolution cache + stats
# ---------------------------------------------------------------------------


class _ResolutionCache:
    """Thread-safe LRU resolution cache with hit/miss stats."""

    def __init__(self, max_size: int = _CACHE_MAX_SIZE) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self.cache_hits = 0
        self.cache_misses = 0

    def get(self, cache_key: str) -> tuple[bool, Any]:
        """Return (hit, value).  Moves the key to end on hit."""
        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                self.cache_hits += 1
                return True, self._cache[cache_key]
            self.cache_misses += 1
            return False, None

    def put(self, cache_key: str, value: Any) -> None:
        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                self._cache[cache_key] = value
            else:
                self._cache[cache_key] = value
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class FlagStats:
    """Evaluation statistics for the flags runtime."""

    cache_hits: int
    cache_misses: int

    def __init__(self, *, cache_hits: int, cache_misses: int) -> None:
        self.cache_hits = cache_hits
        self.cache_misses = cache_misses

    def __repr__(self) -> str:
        return f"FlagStats(cache_hits={self.cache_hits}, cache_misses={self.cache_misses})"


# ---------------------------------------------------------------------------
# Flag registration buffer
# ---------------------------------------------------------------------------


class _FlagRegistrationBuffer:
    """Batches declared flags for bulk registration."""

    def __init__(self) -> None:
        self._seen: OrderedDict[str, bool] = OrderedDict()
        self._pending: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(
        self,
        flag_id: str,
        flag_type: str,
        default: Any,
        service: str | None,
        environment: str | None,
    ) -> None:
        """Queue a flag for registration if not already seen."""
        with self._lock:
            if flag_id not in self._seen:
                self._seen[flag_id] = True
                item: dict[str, Any] = {
                    "id": flag_id,
                    "type": flag_type,
                    "default": default,
                }
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
# FlagsClient (sync)
# ---------------------------------------------------------------------------


class FlagsClient:
    """Synchronous flags runtime namespace.

    Obtained via ``SmplClient(...).flags``. Exposes typed handles
    (``booleanFlag``/``stringFlag``/``numberFlag``/``jsonFlag``) and
    runtime control (``refresh``, ``stats``, ``on_change``,
    ``context_provider``). CRUD has moved to ``mgmt.flags.*``.
    """

    def __init__(
        self,
        parent: SmplClient,
        *,
        flags_base_url: str = _DEFAULT_FLAGS_BASE_URL,
        app_base_url: str = _DEFAULT_APP_BASE_URL,
        context_buffer: _ContextRegistrationBuffer | None = None,
    ) -> None:
        self._parent = parent
        self._flags_http = AuthenticatedClient(
            base_url=flags_base_url,
            token=parent._api_key,
        )
        self._app_http = AuthenticatedClient(
            base_url=app_base_url,
            token=parent._api_key,
        )

        # Runtime state
        self._environment: str | None = None
        self._flag_store: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache = _ResolutionCache()
        self._context_provider: Callable[[], list[Context]] | None = None
        self._context_buffer = context_buffer if context_buffer is not None else _ContextRegistrationBuffer()
        self._flag_buffer = _FlagRegistrationBuffer()
        self._flag_flush_timer: threading.Timer | None = None
        self._handles: dict[str, Flag] = {}
        self._global_listeners: list[Callable[[FlagChangeEvent], None]] = []
        self._key_listeners: dict[str, list[Callable[[FlagChangeEvent], None]]] = {}

        # Shared WebSocket (set during connect)
        self._ws_manager: SharedWebSocket | None = None

    def _close(self) -> None:
        """Release resources held by this client."""
        if self._flag_flush_timer is not None:
            self._flag_flush_timer.cancel()
            self._flag_flush_timer = None

    # ------------------------------------------------------------------
    # Runtime: typed flag handles
    # ------------------------------------------------------------------

    def booleanFlag(self, id: str, *, default: bool) -> BooleanFlag:
        """Declare a boolean flag handle for runtime evaluation."""
        handle = BooleanFlag(self, id=id, name=id, type="BOOLEAN", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "BOOLEAN", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    def stringFlag(self, id: str, *, default: str) -> StringFlag:
        """Declare a string flag handle for runtime evaluation."""
        handle = StringFlag(self, id=id, name=id, type="STRING", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "STRING", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    def numberFlag(self, id: str, *, default: int | float) -> NumberFlag:
        """Declare a numeric flag handle for runtime evaluation."""
        handle = NumberFlag(self, id=id, name=id, type="NUMERIC", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "NUMERIC", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    def jsonFlag(self, id: str, *, default: dict[str, Any]) -> JsonFlag:
        """Declare a JSON flag handle for runtime evaluation."""
        handle = JsonFlag(self, id=id, name=id, type="JSON", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "JSON", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    # ------------------------------------------------------------------
    # Runtime: context provider
    # ------------------------------------------------------------------

    def context_provider(self, fn: Callable[[], list[Context]]) -> Callable[[], list[Context]]:
        """Register a context provider function.  Works as a decorator."""
        self._context_provider = fn
        return fn

    # ------------------------------------------------------------------
    # Runtime: connect / refresh
    # ------------------------------------------------------------------

    def _connect_internal(self) -> None:
        """Lazily initialize: fetch flags, register on shared WebSocket.

        Called automatically on first .get() evaluation, or by start().
        """
        if self._connected:
            return
        self._environment = self._parent._environment

        # Flush discovered flags BEFORE fetching definitions
        self._flush_flags_sync()

        self._fetch_all_flags()
        self._connected = True
        self._cache.clear()

        # Register on the shared WebSocket
        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("flag_changed", self._handle_flag_changed)
        self._ws_manager.on("flag_deleted", self._handle_flag_deleted)
        self._ws_manager.on("flags_changed", self._handle_flags_changed)

        # Start periodic flush timer
        self._schedule_flag_flush()

    def refresh(self) -> None:
        """Re-fetch all flag definitions and clear cache."""
        self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners_all("manual")

    def stats(self) -> FlagStats:
        return FlagStats(cache_hits=self._cache.cache_hits, cache_misses=self._cache.cache_misses)

    # ------------------------------------------------------------------
    # Runtime: change listeners (dual-mode decorator)
    # ------------------------------------------------------------------

    def on_change(self, fn_or_id: Callable[[FlagChangeEvent], None] | str | None = None) -> Any:
        """Register a change listener.

        Supports two forms:

        - ``@client.flags.on_change`` — registers a global listener.
        - ``@client.flags.on_change("flag-id")`` — registers an id-scoped listener.
        """
        if callable(fn_or_id):
            # @on_change (bare decorator)
            self._global_listeners.append(fn_or_id)
            return fn_or_id
        elif isinstance(fn_or_id, str):
            # @on_change("id")
            flag_id = fn_or_id

            def decorator(fn: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
                self._key_listeners.setdefault(flag_id, []).append(fn)
                return fn

            return decorator
        else:
            # @on_change() — called with parens but no args

            def decorator(fn: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
                self._global_listeners.append(fn)
                return fn

            return decorator

    # ------------------------------------------------------------------
    # Internal: context registration flush
    # ------------------------------------------------------------------

    def _flush_contexts_sync(self) -> None:
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            body = _build_bulk_register_body(batch)
            gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        except Exception:
            logger.warning("Context registration flush failed", exc_info=True)

    # ------------------------------------------------------------------
    # Runtime: flag registration flush
    # ------------------------------------------------------------------

    def _flush_flags_sync(self) -> None:
        """Flush the flag registration buffer to the flags service."""
        batch = self._flag_buffer.drain()
        if not batch:
            return
        items = [
            FlagBulkItem(
                id=b["id"],
                type_=b["type"],
                default=b["default"],
                service=b.get("service"),
                environment=b.get("environment"),
            )
            for b in batch
        ]
        body = FlagBulkRequest(flags=items)
        try:
            response = bulk_register_flags.sync_detailed(client=self._flags_http, body=body)
            if response.status_code.value >= 300:
                logger.warning("Bulk flag registration failed: HTTP %s", response.status_code.value)
        except Exception as exc:
            logger.warning("Bulk flag registration failed (flags: %s): %s", self._flags_http._base_url, exc)
            debug("registration", traceback.format_exc().strip())

    def _schedule_flag_flush(self) -> None:
        """Schedule periodic flag registration flush."""

        def _tick() -> None:
            self._flush_flags_sync()
            if self._connected:
                self._schedule_flag_flush()

        self._flag_flush_timer = threading.Timer(_FLAG_BULK_FLUSH_INTERVAL, _tick)
        self._flag_flush_timer.daemon = True
        self._flag_flush_timer.start()

    # ------------------------------------------------------------------
    # Internal: evaluation
    # ------------------------------------------------------------------

    def _evaluate_handle(self, flag_id: str, default: Any, context: list[Context] | None) -> Any:
        """Core evaluation used by flag handles.  Lazily connects on first call."""
        if not self._connected:
            self._connect_internal()

        if context is not None:
            eval_dict = _contexts_to_eval_dict(context)
        else:
            if self._context_provider is not None:
                contexts = self._context_provider()
                eval_dict = _contexts_to_eval_dict(contexts)
                self._context_buffer.observe(contexts)
                if self._context_buffer.pending_count >= _CONTEXT_BATCH_FLUSH_SIZE:
                    threading.Thread(target=self._flush_contexts_sync, daemon=True).start()
            else:
                eval_dict = {}

        # Auto-inject service context if set and not already provided
        if self._parent._service and "service" not in eval_dict:
            eval_dict["service"] = {"key": self._parent._service}

        ctx_hash = _hash_context(eval_dict)
        cache_key = f"{flag_id}:{ctx_hash}"

        hit, cached_value = self._cache.get(cache_key)
        if hit:
            metrics = self._parent._metrics
            if metrics is not None:
                metrics.record("flags.cache_hits", unit="hits")
                metrics.record("flags.evaluations", unit="evaluations", dimensions={"flag": flag_id})
            return cached_value

        flag_def = self._flag_store.get(flag_id)
        if flag_def is None:
            self._cache.put(cache_key, default)
            return default

        value = _evaluate_flag(flag_def, self._environment, eval_dict)
        if value is None:
            value = default

        self._cache.put(cache_key, value)
        metrics = self._parent._metrics
        if metrics is not None:
            metrics.record("flags.cache_misses", unit="misses")
            metrics.record("flags.evaluations", unit="evaluations", dimensions={"flag": flag_id})
        return value

    # ------------------------------------------------------------------
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_flag_changed(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            return
        pre = dict(self._flag_store.get(key, {}))
        new_data = self._fetch_flag_single_data(key)
        self._flag_store[key] = new_data
        self._cache.clear()
        if pre != new_data:
            self._fire_change_listeners(key, "websocket")

    def _handle_flag_deleted(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            return
        existed = key in self._flag_store
        self._flag_store.pop(key, None)
        self._cache.clear()
        if existed:
            self._fire_change_listeners(key, "websocket", deleted=True)

    def _handle_flags_changed(self, data: dict[str, Any]) -> None:
        pre_store = dict(self._flag_store)
        try:
            self._fetch_all_flags()
        except Exception:
            ws_logger.error("Failed to refresh flags after flags_changed WS event", exc_info=True)
            return
        self._cache.clear()
        post_store = self._flag_store
        all_keys = set(pre_store) | set(post_store)
        changed = [k for k in all_keys if pre_store.get(k) != post_store.get(k)]
        if not changed:
            return
        # Global listener fires once
        first_event = FlagChangeEvent(id=changed[0], source="websocket")
        for cb in self._global_listeners:
            try:
                cb(first_event)
            except Exception:
                logger.error("Exception in global flags on_change listener", exc_info=True)
        # Per-key listeners fire for each changed key
        for k in changed:
            deleted = k in pre_store and k not in post_store
            event = FlagChangeEvent(id=k, source="websocket", deleted=deleted)
            for cb in self._key_listeners.get(k, []):
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in id-scoped flags on_change listener", exc_info=True)

    # ------------------------------------------------------------------
    # Internal: flag store
    # ------------------------------------------------------------------

    def _fetch_flag_single_data(self, key: str) -> dict[str, Any]:
        """Fetch a single flag by key and return a store-format dict."""
        try:
            response = get_flag.sync_detailed(key, client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._flags_http._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        d = _flag_dict_from_json(body["data"])
        return {
            "id": d["id"],
            "name": d["name"],
            "type": d["type"],
            "default": d["default"],
            "values": d["values"],
            "description": d["description"],
            "environments": d["environments"],
        }

    def _fetch_all_flags(self) -> None:
        flags = self._fetch_flags_list()
        self._flag_store = {f["id"]: f for f in flags}

    def _fetch_flags_list(self) -> list[dict[str, Any]]:
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._flags_http._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        result = []
        for r in body.get("data", []):
            d = _flag_dict_from_json(r)
            result.append(
                {
                    "id": d["id"],
                    "name": d["name"],
                    "type": d["type"],
                    "default": d["default"],
                    "values": d["values"],
                    "description": d["description"],
                    "environments": d["environments"],
                }
            )
        return result

    def _fire_change_listeners(self, flag_id: str | None, source: str, *, deleted: bool = False) -> None:
        if flag_id:
            event = FlagChangeEvent(id=flag_id, source=source, deleted=deleted)
            for cb in self._global_listeners:
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in global flags on_change listener", exc_info=True)
            for cb in self._key_listeners.get(flag_id, []):
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in id-scoped flags on_change listener", exc_info=True)

    def _fire_change_listeners_all(self, source: str) -> None:
        for flag_id in self._flag_store:
            self._fire_change_listeners(flag_id, source)


# ---------------------------------------------------------------------------
# AsyncFlagsClient
# ---------------------------------------------------------------------------


class AsyncFlagsClient:
    """Asynchronous flags runtime namespace.  Obtained via ``AsyncSmplClient(...).flags``.

    CRUD has moved to ``AsyncSmplManagementClient.flags`` (``mgmt.flags.*``).
    """

    def __init__(
        self,
        parent: AsyncSmplClient,
        *,
        flags_base_url: str = _DEFAULT_FLAGS_BASE_URL,
        app_base_url: str = _DEFAULT_APP_BASE_URL,
        context_buffer: _ContextRegistrationBuffer | None = None,
    ) -> None:
        self._parent = parent
        self._flags_http = AuthenticatedClient(
            base_url=flags_base_url,
            token=parent._api_key,
        )
        self._app_http = AuthenticatedClient(
            base_url=app_base_url,
            token=parent._api_key,
        )

        # Runtime state
        self._environment: str | None = None
        self._flag_store: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache = _ResolutionCache()
        self._context_provider: Callable[[], list[Context]] | None = None
        self._context_buffer = context_buffer if context_buffer is not None else _ContextRegistrationBuffer()
        self._flag_buffer = _FlagRegistrationBuffer()
        self._flag_flush_timer: threading.Timer | None = None
        self._handles: dict[str, AsyncFlag] = {}
        self._global_listeners: list[Callable[[FlagChangeEvent], None]] = []
        self._key_listeners: dict[str, list[Callable[[FlagChangeEvent], None]]] = {}

        # Shared WebSocket (set during connect)
        self._ws_manager: SharedWebSocket | None = None

    def _close(self) -> None:
        """Release resources held by this client."""
        if self._flag_flush_timer is not None:
            self._flag_flush_timer.cancel()
            self._flag_flush_timer = None

    # ------------------------------------------------------------------
    # Runtime: typed flag handles
    # ------------------------------------------------------------------

    def booleanFlag(self, id: str, *, default: bool) -> AsyncBooleanFlag:
        handle = AsyncBooleanFlag(self, id=id, name=id, type="BOOLEAN", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "BOOLEAN", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    def stringFlag(self, id: str, *, default: str) -> AsyncStringFlag:
        handle = AsyncStringFlag(self, id=id, name=id, type="STRING", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "STRING", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    def numberFlag(self, id: str, *, default: int | float) -> AsyncNumberFlag:
        handle = AsyncNumberFlag(self, id=id, name=id, type="NUMERIC", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "NUMERIC", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    def jsonFlag(self, id: str, *, default: dict[str, Any]) -> AsyncJsonFlag:
        handle = AsyncJsonFlag(self, id=id, name=id, type="JSON", default=default)
        self._handles[id] = handle
        self._flag_buffer.add(id, "JSON", default, self._parent._service, self._parent._environment)
        if self._flag_buffer.pending_count >= _FLAG_BULK_FLUSH_THRESHOLD:
            threading.Thread(target=self._flush_flags_sync, daemon=True).start()
        return handle

    # ------------------------------------------------------------------
    # Runtime: context provider
    # ------------------------------------------------------------------

    def context_provider(self, fn: Callable[[], list[Context]]) -> Callable[[], list[Context]]:
        self._context_provider = fn
        return fn

    # ------------------------------------------------------------------
    # Runtime: connect / refresh
    # ------------------------------------------------------------------

    async def _connect_internal(self) -> None:
        """Lazily initialize: fetch flags, register on shared WebSocket."""
        if self._connected:
            return
        self._environment = self._parent._environment

        # Flush discovered flags BEFORE fetching definitions
        await self._flush_flags_async()

        await self._fetch_all_flags()
        self._connected = True
        self._cache.clear()

        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("flag_changed", self._handle_flag_changed)
        self._ws_manager.on("flag_deleted", self._handle_flag_deleted)
        self._ws_manager.on("flags_changed", self._handle_flags_changed)

        # Start periodic flush timer
        self._schedule_flag_flush()

    async def refresh(self) -> None:
        await self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners_all("manual")

    def stats(self) -> FlagStats:
        return FlagStats(cache_hits=self._cache.cache_hits, cache_misses=self._cache.cache_misses)

    # ------------------------------------------------------------------
    # Runtime: change listeners (dual-mode decorator)
    # ------------------------------------------------------------------

    def on_change(self, fn_or_id: Callable[[FlagChangeEvent], None] | str | None = None) -> Any:
        """Register a change listener (global or id-scoped)."""
        if callable(fn_or_id):
            self._global_listeners.append(fn_or_id)
            return fn_or_id
        elif isinstance(fn_or_id, str):
            flag_id = fn_or_id

            def decorator(fn: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
                self._key_listeners.setdefault(flag_id, []).append(fn)
                return fn

            return decorator
        else:

            def decorator(fn: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
                self._global_listeners.append(fn)
                return fn

            return decorator

    # ------------------------------------------------------------------
    # Internal: context registration flush
    # ------------------------------------------------------------------

    async def _flush_contexts_async(self) -> None:
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            body = _build_bulk_register_body(batch)
            await gen_bulk_register_contexts.asyncio_detailed(client=self._app_http, body=body)
        except Exception:
            logger.warning("Context registration flush failed", exc_info=True)

    # ------------------------------------------------------------------
    # Runtime: flag registration flush
    # ------------------------------------------------------------------

    async def _flush_flags_async(self) -> None:
        """Flush the flag registration buffer to the flags service (async)."""
        batch = self._flag_buffer.drain()
        if not batch:
            return
        items = [
            FlagBulkItem(
                id=b["id"],
                type_=b["type"],
                default=b["default"],
                service=b.get("service"),
                environment=b.get("environment"),
            )
            for b in batch
        ]
        body = FlagBulkRequest(flags=items)
        try:
            response = await bulk_register_flags.asyncio_detailed(client=self._flags_http, body=body)
            if response.status_code.value >= 300:
                logger.warning("Bulk flag registration failed: HTTP %s", response.status_code.value)
        except Exception as exc:
            logger.warning("Bulk flag registration failed (flags: %s): %s", self._flags_http._base_url, exc)
            debug("registration", traceback.format_exc().strip())

    def _flush_flags_sync(self) -> None:
        """Sync flush for periodic timer (runs in background thread)."""
        batch = self._flag_buffer.drain()
        if not batch:
            return
        items = [
            FlagBulkItem(
                id=b["id"],
                type_=b["type"],
                default=b["default"],
                service=b.get("service"),
                environment=b.get("environment"),
            )
            for b in batch
        ]
        body = FlagBulkRequest(flags=items)
        try:
            response = bulk_register_flags.sync_detailed(client=self._flags_http, body=body)
            if response.status_code.value >= 300:
                logger.warning("Bulk flag registration failed: HTTP %s", response.status_code.value)
        except Exception as exc:
            logger.warning("Bulk flag registration failed (flags: %s): %s", self._flags_http._base_url, exc)
            debug("registration", traceback.format_exc().strip())

    def _schedule_flag_flush(self) -> None:
        """Schedule periodic flag registration flush."""

        def _tick() -> None:
            self._flush_flags_sync()
            if self._connected:
                self._schedule_flag_flush()

        self._flag_flush_timer = threading.Timer(_FLAG_BULK_FLUSH_INTERVAL, _tick)
        self._flag_flush_timer.daemon = True
        self._flag_flush_timer.start()

    # ------------------------------------------------------------------
    # Internal: evaluation
    # ------------------------------------------------------------------

    def _evaluate_handle(self, flag_id: str, default: Any, context: list[Context] | None) -> Any:
        """Core evaluation used by flag handles.  Lazily connects on first call.

        Note: This is synchronous.  The async client's _connect_internal is
        async, so we use sync HTTP calls for the initial fetch (called from
        the WebSocket background thread as well).
        """
        if not self._connected:
            # Lazy init using sync HTTP (safe from any thread)
            self._environment = self._parent._environment
            self._flush_flags_sync()
            self._fetch_all_flags_sync()
            self._connected = True
            self._cache.clear()
            self._ws_manager = self._parent._ensure_ws()
            self._ws_manager.on("flag_changed", self._handle_flag_changed)
            self._ws_manager.on("flag_deleted", self._handle_flag_deleted)
            self._ws_manager.on("flags_changed", self._handle_flags_changed)
            self._schedule_flag_flush()

        if context is not None:
            eval_dict = _contexts_to_eval_dict(context)
        else:
            if self._context_provider is not None:
                contexts = self._context_provider()
                eval_dict = _contexts_to_eval_dict(contexts)
                self._context_buffer.observe(contexts)
                if self._context_buffer.pending_count >= _CONTEXT_BATCH_FLUSH_SIZE:
                    threading.Thread(target=self._flush_contexts_bg, daemon=True).start()
            else:
                eval_dict = {}

        if self._parent._service and "service" not in eval_dict:
            eval_dict["service"] = {"key": self._parent._service}

        ctx_hash = _hash_context(eval_dict)
        cache_key = f"{flag_id}:{ctx_hash}"

        hit, cached_value = self._cache.get(cache_key)
        if hit:
            metrics = self._parent._metrics
            if metrics is not None:
                metrics.record("flags.cache_hits", unit="hits")
                metrics.record("flags.evaluations", unit="evaluations", dimensions={"flag": flag_id})
            return cached_value

        flag_def = self._flag_store.get(flag_id)
        if flag_def is None:
            self._cache.put(cache_key, default)
            return default

        value = _evaluate_flag(flag_def, self._environment, eval_dict)
        if value is None:
            value = default

        self._cache.put(cache_key, value)
        metrics = self._parent._metrics
        if metrics is not None:
            metrics.record("flags.cache_misses", unit="misses")
            metrics.record("flags.evaluations", unit="evaluations", dimensions={"flag": flag_id})
        return value

    def _flush_contexts_bg(self) -> None:
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            body = _build_bulk_register_body(batch)
            gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        except Exception:
            logger.warning("Context registration flush failed", exc_info=True)

    # ------------------------------------------------------------------
    # Internal: flag store
    # ------------------------------------------------------------------

    async def _fetch_all_flags(self) -> None:
        flags = await self._fetch_flags_list()
        self._flag_store = {f["id"]: f for f in flags}

    async def _fetch_flags_list(self) -> list[dict[str, Any]]:
        try:
            response = await list_flags.asyncio_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._flags_http._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        result = []
        for r in body.get("data", []):
            d = _flag_dict_from_json(r)
            result.append(
                {
                    "id": d["id"],
                    "name": d["name"],
                    "type": d["type"],
                    "default": d["default"],
                    "values": d["values"],
                    "description": d["description"],
                    "environments": d["environments"],
                }
            )
        return result

    def _fetch_all_flags_sync(self) -> None:
        """Sync fetch for lazy init from _evaluate_handle."""
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._flags_http._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        store: dict[str, dict[str, Any]] = {}
        for r in body.get("data", []):
            d = _flag_dict_from_json(r)
            store[d["id"]] = {
                "id": d["id"],
                "name": d["name"],
                "type": d["type"],
                "default": d["default"],
                "values": d["values"],
                "description": d["description"],
                "environments": d["environments"],
            }
        self._flag_store = store

    def _fetch_flag_single_data_sync(self, key: str) -> dict[str, Any]:
        """Sync fetch of a single flag by key (used from WS event handlers)."""
        try:
            response = get_flag.sync_detailed(key, client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc, self._flags_http._base_url)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        d = _flag_dict_from_json(body["data"])
        return {
            "id": d["id"],
            "name": d["name"],
            "type": d["type"],
            "default": d["default"],
            "values": d["values"],
            "description": d["description"],
            "environments": d["environments"],
        }

    # ------------------------------------------------------------------
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_flag_changed(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            return
        pre = dict(self._flag_store.get(key, {}))
        try:
            new_data = self._fetch_flag_single_data_sync(key)
        except Exception:
            ws_logger.error("Failed to fetch flag %r after WS event", key, exc_info=True)
            return
        self._flag_store[key] = new_data
        self._cache.clear()
        if pre != new_data:
            self._fire_change_listeners(key, "websocket")

    def _handle_flag_deleted(self, data: dict[str, Any]) -> None:
        key = data.get("id")
        if not key:
            return
        existed = key in self._flag_store
        self._flag_store.pop(key, None)
        self._cache.clear()
        if existed:
            self._fire_change_listeners(key, "websocket", deleted=True)

    def _handle_flags_changed(self, data: dict[str, Any]) -> None:
        pre_store = dict(self._flag_store)
        try:
            self._fetch_all_flags_sync()
        except Exception:
            ws_logger.error("Failed to refresh flags after flags_changed WS event", exc_info=True)
            return
        self._cache.clear()
        post_store = self._flag_store
        all_keys = set(pre_store) | set(post_store)
        changed = [k for k in all_keys if pre_store.get(k) != post_store.get(k)]
        if not changed:
            return
        first_event = FlagChangeEvent(id=changed[0], source="websocket")
        for cb in self._global_listeners:
            try:
                cb(first_event)
            except Exception:
                logger.error("Exception in global flags on_change listener", exc_info=True)
        for k in changed:
            deleted = k in pre_store and k not in post_store
            event = FlagChangeEvent(id=k, source="websocket", deleted=deleted)
            for cb in self._key_listeners.get(k, []):
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in id-scoped flags on_change listener", exc_info=True)

    def _fire_change_listeners(self, flag_id: str | None, source: str, *, deleted: bool = False) -> None:
        if flag_id:
            event = FlagChangeEvent(id=flag_id, source=source, deleted=deleted)
            for cb in self._global_listeners:
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in global flags on_change listener", exc_info=True)
            for cb in self._key_listeners.get(flag_id, []):
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in id-scoped flags on_change listener", exc_info=True)

    def _fire_change_listeners_all(self, source: str) -> None:
        for flag_id in self._flag_store:
            self._fire_change_listeners(flag_id, source)


# ---------------------------------------------------------------------------
# Helpers: context registration
# ---------------------------------------------------------------------------


def _build_bulk_register_body(batch: list[dict[str, Any]]) -> ContextBulkRegister:
    """Convert a list of context dicts to a ContextBulkRegister model."""
    items: list[ContextBulkItem] = []
    for ctx in batch:
        item_attrs_dict = ctx.get("attributes")
        if item_attrs_dict:
            item_attrs = ContextBulkItemAttributes()
            item_attrs.additional_properties = dict(item_attrs_dict)
            items.append(ContextBulkItem(type_=ctx["type"], key=ctx["key"], attributes=item_attrs))
        else:
            items.append(ContextBulkItem(type_=ctx["type"], key=ctx["key"]))
    return ContextBulkRegister(contexts=items)


# ---------------------------------------------------------------------------
# JSON Logic evaluation
# ---------------------------------------------------------------------------


def _evaluate_flag(flag_def: dict[str, Any], environment: str | None, eval_dict: dict[str, Any]) -> Any:
    """Evaluate a flag definition against the given context.

    Follows ADR-022 §2.6 semantics:
    1. Look up the environment.  If missing, return flag-level default.
    2. If disabled, return env default or flag default.
    3. Iterate rules; first match wins.
    4. No match → env default or flag default.
    """
    from json_logic import jsonLogic

    flag_default = flag_def.get("default")
    environments = flag_def.get("environments", {})

    if environment is None or environment not in environments:
        return flag_default

    env_config = environments[environment]
    env_default = env_config.get("default")
    fallback = env_default if env_default is not None else flag_default

    if not env_config.get("enabled", False):
        return fallback

    rules = env_config.get("rules", [])
    for rule in rules:
        logic = rule.get("logic", {})
        if not logic:
            continue
        try:
            result = jsonLogic(logic, eval_dict)
            if result:
                return rule.get("value")
        except Exception:
            logger.warning("JSON Logic evaluation error for rule %r", rule, exc_info=True)
            continue

    return fallback
