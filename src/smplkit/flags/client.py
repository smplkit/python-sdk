"""FlagsClient and AsyncFlagsClient — management + runtime for Smpl Flags."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from smplkit._errors import (
    SmplConnectionError,
    SmplNotConnectedError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit._generated.flags.api.flags import (
    create_flag,
    delete_flag,
    get_flag,
    list_flags,
    update_flag,
)
from smplkit._generated.flags.client import AuthenticatedClient
from smplkit._generated.flags.models.flag import Flag as GenFlag
from smplkit._generated.flags.models.flag_environment import FlagEnvironment as GenFlagEnvironment
from smplkit._generated.flags.models.flag_environments import FlagEnvironments as GenFlagEnvironments
from smplkit._generated.flags.models.flag_rule import FlagRule as GenFlagRule
from smplkit._generated.flags.models.flag_rule_logic import FlagRuleLogic as GenFlagRuleLogic
from smplkit._generated.flags.models.flag_value import FlagValue as GenFlagValue
from smplkit._generated.flags.models.resource_flag import ResourceFlag
from smplkit._generated.flags.models.response_flag import ResponseFlag
from smplkit.flags.models import AsyncFlag, ContextType, Flag

if TYPE_CHECKING:
    from smplkit._ws import SharedWebSocket
    from smplkit.client import AsyncSmplClient, SmplClient
    from smplkit.flags.types import Context, FlagType

logger = logging.getLogger("smplkit")
ws_logger = logging.getLogger("smplkit.flags.ws")

_DEFAULT_FLAGS_BASE_URL = "https://flags.smplkit.com"
_DEFAULT_APP_BASE_URL = "https://app.smplkit.com"
_CACHE_MAX_SIZE = 10_000
_CONTEXT_REGISTRATION_LRU_SIZE = 10_000
_CONTEXT_BATCH_FLUSH_SIZE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_response_status(status_code: Any, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions."""
    code = int(status_code)
    if code == 404:
        raise SmplNotFoundError(content.decode("utf-8", errors="replace"))
    if code == 409:
        from smplkit._errors import SmplConflictError

        raise SmplConflictError(content.decode("utf-8", errors="replace"))
    if code == 422:
        raise SmplValidationError(content.decode("utf-8", errors="replace"))


def _maybe_reraise_network_error(exc: Exception) -> None:
    """Re-raise httpx exceptions as SDK exceptions if applicable."""
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        raise SmplTimeoutError(str(exc)) from exc
    if isinstance(exc, httpx.HTTPError):
        raise SmplConnectionError(str(exc)) from exc
    if isinstance(exc, (SmplNotFoundError, SmplValidationError)):
        raise exc


def _extract_environments(environments: Any) -> dict[str, Any]:
    """Extract environments from a generated FlagEnvironments object to plain dicts."""
    from smplkit._generated.flags.types import UNSET

    if environments is None or isinstance(environments, type(UNSET)):
        return {}
    type_name = type(environments).__name__
    if type_name == "Unset":
        return {}
    if isinstance(environments, GenFlagEnvironments):
        result: dict[str, Any] = {}
        for env_name, env_obj in environments.additional_properties.items():
            entry: dict[str, Any] = {}
            if not isinstance(env_obj.enabled, type(UNSET)):
                entry["enabled"] = env_obj.enabled
            default_val = env_obj.default
            if not isinstance(default_val, type(UNSET)):
                entry["default"] = default_val
            rules_val = env_obj.rules
            if not isinstance(rules_val, type(UNSET)):
                entry["rules"] = [_extract_rule(r) for r in rules_val]
            else:
                entry["rules"] = []
            result[env_name] = entry
        return result
    if isinstance(environments, dict):
        return dict(environments)
    return {}


def _extract_rule(rule: Any) -> dict[str, Any]:
    """Extract a FlagRule to a plain dict."""
    from smplkit._generated.flags.types import UNSET

    result: dict[str, Any] = {
        "logic": dict(rule.logic.additional_properties) if hasattr(rule.logic, "additional_properties") else {},
        "value": rule.value,
    }
    if not isinstance(rule.description, type(UNSET)) and rule.description is not None:
        result["description"] = rule.description
    return result


def _extract_values(values: Any) -> list[dict[str, Any]]:
    """Extract a list of FlagValue to plain dicts."""
    if not values:
        return []
    result = []
    for v in values:
        entry: dict[str, Any] = {"name": v.name, "value": v.value}
        result.append(entry)
    return result


def _unset_to_none(value: Any) -> Any:
    """Convert Unset sentinels to None."""
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _build_gen_flag(
    *,
    key: str,
    name: str,
    type_: str,
    default: Any,
    values: list[dict[str, Any]],
    description: str | None = None,
    environments: dict[str, Any] | None = None,
) -> GenFlag:
    """Build a generated Flag model from plain values."""
    gen_values = [GenFlagValue(name=v["name"], value=v["value"]) for v in values]

    gen_envs: GenFlagEnvironments | Any
    if environments:
        gen_envs = GenFlagEnvironments()
        env_props: dict[str, GenFlagEnvironment] = {}
        for env_name, env_data in environments.items():
            rules = []
            for r in env_data.get("rules", []):
                logic_obj = GenFlagRuleLogic()
                logic_obj.additional_properties = dict(r.get("logic", {}))
                rule_obj = GenFlagRule(
                    logic=logic_obj,
                    value=r.get("value"),
                    description=r.get("description"),
                )
                rules.append(rule_obj)
            env_obj = GenFlagEnvironment(
                enabled=env_data.get("enabled", False),
                default=env_data.get("default"),
                rules=rules,
            )
            env_props[env_name] = env_obj
        gen_envs.additional_properties = env_props
    else:
        from smplkit._generated.flags.types import UNSET

        gen_envs = UNSET

    return GenFlag(
        key=key,
        name=name,
        type_=type_,
        default=default,
        values=gen_values,
        description=description,
        environments=gen_envs,
    )


def _build_request_body(gen_flag: GenFlag) -> ResponseFlag:
    """Wrap a generated Flag in the JSON:API request envelope."""
    resource = ResourceFlag(attributes=gen_flag, type_="flag")
    return ResponseFlag(data=resource)


def _contexts_to_eval_dict(contexts: list[Context]) -> dict[str, Any]:
    """Convert a list of Context objects to the nested evaluation dict.

    Each Context's type becomes a top-level key.  The key field is
    injected alongside attributes.
    """
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

    def __init__(self, *, key: str, source: str) -> None:
        self.key = key
        self.source = source

    def __repr__(self) -> str:
        return f"FlagChangeEvent(key={self.key!r}, source={self.source!r})"


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
    """Cache statistics for the flags runtime."""

    def __init__(self, *, cache_hits: int, cache_misses: int) -> None:
        self.cache_hits = cache_hits
        self.cache_misses = cache_misses

    def __repr__(self) -> str:
        return f"FlagStats(cache_hits={self.cache_hits}, cache_misses={self.cache_misses})"


# ---------------------------------------------------------------------------
# Typed flag handles
# ---------------------------------------------------------------------------


class _FlagHandle:
    """Base for typed flag handles."""

    def __init__(self, namespace: Any, key: str, default: Any) -> None:
        self._namespace = namespace
        self._key = key
        self._default = default
        self._listeners: list[Callable[[FlagChangeEvent], None]] = []

    @property
    def key(self) -> str:
        return self._key

    @property
    def default(self) -> Any:
        return self._default

    def get(self, context: list[Context] | None = None) -> Any:
        return self._namespace._evaluate_handle(self._key, self._default, context)

    def on_change(self, callback: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
        """Register a flag-specific change listener.  Works as a decorator."""
        self._listeners.append(callback)
        return callback


class BoolFlagHandle(_FlagHandle):
    """Typed handle for a boolean flag."""

    def get(self, context: list[Context] | None = None) -> bool:
        value = self._namespace._evaluate_handle(self._key, self._default, context)
        if isinstance(value, bool):
            return value
        return self._default


class StringFlagHandle(_FlagHandle):
    """Typed handle for a string flag."""

    def get(self, context: list[Context] | None = None) -> str:
        value = self._namespace._evaluate_handle(self._key, self._default, context)
        if isinstance(value, str):
            return value
        return self._default


class NumberFlagHandle(_FlagHandle):
    """Typed handle for a numeric flag."""

    def get(self, context: list[Context] | None = None) -> int | float:
        value = self._namespace._evaluate_handle(self._key, self._default, context)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        return self._default


class JsonFlagHandle(_FlagHandle):
    """Typed handle for a JSON flag."""

    def get(self, context: list[Context] | None = None) -> dict[str, Any]:
        value = self._namespace._evaluate_handle(self._key, self._default, context)
        if isinstance(value, dict):
            return value
        return self._default


# ---------------------------------------------------------------------------
# Context registration buffer
# ---------------------------------------------------------------------------


class _ContextRegistrationBuffer:
    """Batches newly-observed context instances for background registration."""

    def __init__(self) -> None:
        self._seen: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._pending: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def observe(self, contexts: list[Context]) -> None:
        """Record contexts from a provider call.  Queue unseen ones."""
        with self._lock:
            for ctx in contexts:
                cache_key = (ctx.type, ctx.key)
                if cache_key not in self._seen:
                    if len(self._seen) >= _CONTEXT_REGISTRATION_LRU_SIZE:
                        self._seen.popitem(last=False)
                    self._seen[cache_key] = ctx.attributes
                    item: dict[str, Any] = {
                        "type": ctx.type,
                        "key": ctx.key,
                        "attributes": dict(ctx.attributes),
                    }
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
    """Synchronous flags namespace.  Obtained via ``SmplClient(...).flags``."""

    def __init__(self, parent: SmplClient) -> None:
        self._parent = parent
        self._flags_http = AuthenticatedClient(
            base_url=_DEFAULT_FLAGS_BASE_URL,
            token=parent._api_key,
        )
        self._app_http = AuthenticatedClient(
            base_url=_DEFAULT_APP_BASE_URL,
            token=parent._api_key,
        )

        # Runtime state
        self._environment: str | None = None
        self._flag_store: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache = _ResolutionCache()
        self._context_provider: Callable[[], list[Context]] | None = None
        self._context_buffer = _ContextRegistrationBuffer()
        self._handles: dict[str, _FlagHandle] = {}
        self._global_listeners: list[Callable[[FlagChangeEvent], None]] = []

        # Shared WebSocket (set during connect)
        self._ws_manager: SharedWebSocket | None = None

    # ------------------------------------------------------------------
    # Management methods
    # ------------------------------------------------------------------

    def create(
        self,
        key: str,
        *,
        name: str,
        type: FlagType,
        default: Any,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> Flag:
        """Create a flag."""
        from smplkit.flags.types import FlagType as FT

        if values is None and type == FT.BOOLEAN:
            values = [{"name": "True", "value": True}, {"name": "False", "value": False}]

        gen_flag = _build_gen_flag(
            key=key,
            name=name,
            type_=type.value if isinstance(type, FT) else str(type),
            default=default,
            values=values or [],
            description=description,
        )
        body = _build_request_body(gen_flag)
        try:
            response = create_flag.sync_detailed(client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to create flag")
        return self._to_model(response.parsed)

    def get(self, flag_id: str) -> Flag:
        """Fetch a flag by UUID."""
        from uuid import UUID

        try:
            response = get_flag.sync_detailed(UUID(flag_id), client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Flag {flag_id} not found")
        return self._to_model(response.parsed)

    def list(self) -> list[Flag]:
        """List all flags."""
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._resource_to_model(r) for r in response.parsed.data]

    def delete(self, flag_id: str) -> None:
        """Delete a flag by UUID."""
        from uuid import UUID

        try:
            response = delete_flag.sync_detailed(UUID(flag_id), client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    def _update_flag(
        self,
        *,
        flag: Flag,
        environments: dict[str, Any] | None = None,
        values: list[dict[str, Any]] | None = None,
        default: Any = None,
        description: str | None = None,
        name: str | None = None,
    ) -> Flag:
        """Internal: PUT a full flag update."""
        from uuid import UUID

        gen_flag = _build_gen_flag(
            key=flag.key,
            name=name if name is not None else flag.name,
            type_=flag.type,
            default=default if default is not None else flag.default,
            values=values if values is not None else flag.values,
            description=description if description is not None else flag.description,
            environments=environments if environments is not None else flag.environments,
        )
        body = _build_request_body(gen_flag)
        try:
            response = update_flag.sync_detailed(UUID(flag.id), client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to update flag")
        return self._to_model(response.parsed)

    # ------------------------------------------------------------------
    # Context type management (direct HTTP — no generated client)
    # ------------------------------------------------------------------

    def create_context_type(self, key: str, *, name: str) -> ContextType:
        """Create a context type."""
        resp = self._app_http.get_httpx_client().post(
            "/api/v1/context_types",
            json={"data": {"type": "context_type", "attributes": {"key": key, "name": name}}},
        )
        _check_response_status(resp.status_code, resp.content)
        data = resp.json().get("data", {})
        return self._parse_context_type(data)

    def update_context_type(self, ct_id: str, *, attributes: dict[str, Any]) -> ContextType:
        """Update a context type (merge attributes)."""
        resp = self._app_http.get_httpx_client().put(
            f"/api/v1/context_types/{ct_id}",
            json={"data": {"type": "context_type", "attributes": {"attributes": attributes}}},
        )
        _check_response_status(resp.status_code, resp.content)
        data = resp.json().get("data", {})
        return self._parse_context_type(data)

    def list_context_types(self) -> list[ContextType]:
        """List all context types."""
        resp = self._app_http.get_httpx_client().get("/api/v1/context_types")
        _check_response_status(resp.status_code, resp.content)
        items = resp.json().get("data", [])
        return [self._parse_context_type(item) for item in items]

    def delete_context_type(self, ct_id: str) -> None:
        """Delete a context type."""
        resp = self._app_http.get_httpx_client().delete(f"/api/v1/context_types/{ct_id}")
        _check_response_status(resp.status_code, resp.content)

    def list_contexts(self, *, context_type_key: str) -> list[dict[str, Any]]:
        """List context instances filtered by context_type_key."""
        params = {"filter[context_type]": context_type_key}
        resp = self._app_http.get_httpx_client().get("/api/v1/contexts", params=params)
        _check_response_status(resp.status_code, resp.content)
        return resp.json().get("data", [])

    # ------------------------------------------------------------------
    # Runtime: typed flag handles
    # ------------------------------------------------------------------

    def boolFlag(self, key: str, default: bool) -> BoolFlagHandle:
        handle = BoolFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    def stringFlag(self, key: str, default: str) -> StringFlagHandle:
        handle = StringFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    def numberFlag(self, key: str, default: int | float) -> NumberFlagHandle:
        handle = NumberFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    def jsonFlag(self, key: str, default: dict[str, Any]) -> JsonFlagHandle:
        handle = JsonFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    # ------------------------------------------------------------------
    # Runtime: context provider
    # ------------------------------------------------------------------

    def context_provider(self, fn: Callable[[], list[Context]]) -> Callable[[], list[Context]]:
        """Register a context provider function.  Works as a decorator."""
        self._context_provider = fn
        return fn

    # ------------------------------------------------------------------
    # Runtime: connect / disconnect / refresh
    # ------------------------------------------------------------------

    def _connect_internal(self) -> None:
        """Connect to the environment: fetch flags, register on shared WebSocket.

        Called by :meth:`SmplClient.connect`. Uses the environment set on the
        parent client.
        """
        self._environment = self._parent._environment
        self._fetch_all_flags()
        self._connected = True
        self._cache.clear()

        # Register on the shared WebSocket
        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("flag_changed", self._handle_flag_changed)
        self._ws_manager.on("flag_deleted", self._handle_flag_deleted)

    def disconnect(self) -> None:
        """Disconnect: unregister from WebSocket, flush contexts, clear state."""
        # Unregister from the shared WebSocket
        if self._ws_manager is not None:
            self._ws_manager.off("flag_changed", self._handle_flag_changed)
            self._ws_manager.off("flag_deleted", self._handle_flag_deleted)
            self._ws_manager = None

        self._flush_contexts_sync()
        self._flag_store.clear()
        self._cache.clear()
        self._connected = False
        self._environment = None

    def refresh(self) -> None:
        """Re-fetch all flag definitions and clear cache."""
        self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners_all("manual")

    def connection_status(self) -> str:
        if self._ws_manager is not None:
            return self._ws_manager.connection_status
        return "disconnected"

    def stats(self) -> FlagStats:
        return FlagStats(cache_hits=self._cache.cache_hits, cache_misses=self._cache.cache_misses)

    # ------------------------------------------------------------------
    # Runtime: change listeners
    # ------------------------------------------------------------------

    def on_change(self, callback: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
        """Register a global change listener.  Works as a decorator."""
        self._global_listeners.append(callback)
        return callback

    # ------------------------------------------------------------------
    # Runtime: context registration
    # ------------------------------------------------------------------

    def register(self, context: Context | list[Context]) -> None:
        """Explicitly register context(s) for background batch registration.

        Accepts a single :class:`Context` or a list.  Queues into the same
        batch buffer used by the automatic context provider side-effect.
        Fire-and-forget — never blocks, never raises on registration failure.

        Works before ``connect()`` is called; contexts are queued locally
        and flushed when the connection is established or
        ``flush_contexts()`` is called.
        """
        if isinstance(context, list):
            self._context_buffer.observe(context)
        else:
            self._context_buffer.observe([context])

    def flush_contexts(self) -> None:
        """Flush pending context registrations to the server."""
        self._flush_contexts_sync()

    def _flush_contexts_sync(self) -> None:
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            self._app_http.get_httpx_client().put(
                "/api/v1/contexts/bulk",
                json={"contexts": batch},
            )
        except Exception:
            logger.debug("Context registration flush failed", exc_info=True)

    # ------------------------------------------------------------------
    # Runtime: Tier 1 evaluate
    # ------------------------------------------------------------------

    def evaluate(self, key: str, *, environment: str, context: list[Context]) -> Any:
        """Tier 1 explicit evaluation — stateless, no provider or cache."""
        eval_dict = _contexts_to_eval_dict(context)

        # Auto-inject service context if set and not already provided
        if self._parent._service and "service" not in eval_dict:
            eval_dict["service"] = {"key": self._parent._service}

        # Use local store if connected, otherwise fetch
        if self._connected and key in self._flag_store:
            flag_def = self._flag_store[key]
        else:
            flags = self._fetch_flags_list()
            flag_def = None
            for f in flags:
                if f.get("key") == key:
                    flag_def = f
                    break
            if flag_def is None:
                return None

        return _evaluate_flag(flag_def, environment, eval_dict)

    # ------------------------------------------------------------------
    # Internal: evaluation
    # ------------------------------------------------------------------

    def _evaluate_handle(self, key: str, default: Any, context: list[Context] | None) -> Any:
        """Core evaluation used by flag handles."""
        if not self._connected:
            raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")

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
        cache_key = f"{key}:{ctx_hash}"

        hit, cached_value = self._cache.get(cache_key)
        if hit:
            return cached_value

        flag_def = self._flag_store.get(key)
        if flag_def is None:
            self._cache.put(cache_key, default)
            return default

        value = _evaluate_flag(flag_def, self._environment, eval_dict)
        if value is None:
            value = default

        self._cache.put(cache_key, value)
        return value

    # ------------------------------------------------------------------
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_flag_changed(self, data: dict[str, Any]) -> None:
        """Handle a flag_changed event by re-fetching all flags."""
        flag_key = data.get("key")
        self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners(flag_key, "websocket")

    def _handle_flag_deleted(self, data: dict[str, Any]) -> None:
        """Handle a flag_deleted event by re-fetching all flags."""
        flag_key = data.get("key")
        self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners(flag_key, "websocket")

    # ------------------------------------------------------------------
    # Internal: flag store
    # ------------------------------------------------------------------

    def _fetch_all_flags(self) -> None:
        """Fetch all flags and store as plain dicts keyed by flag key."""
        flags = self._fetch_flags_list()
        self._flag_store = {f["key"]: f for f in flags}

    def _fetch_flags_list(self) -> list[dict[str, Any]]:
        """Fetch all flags as plain dicts."""
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        result = []
        for r in response.parsed.data:
            attrs = r.attributes
            result.append(
                {
                    "key": attrs.key,
                    "name": attrs.name,
                    "type": attrs.type_,
                    "default": attrs.default,
                    "values": _extract_values(attrs.values),
                    "description": _unset_to_none(attrs.description),
                    "environments": _extract_environments(attrs.environments),
                }
            )
        return result

    def _fire_change_listeners(self, flag_key: str | None, source: str) -> None:
        """Fire global and flag-specific listeners for a single flag."""
        if flag_key:
            event = FlagChangeEvent(key=flag_key, source=source)
            for cb in self._global_listeners:
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in global flags on_change listener", exc_info=True)
            handle = self._handles.get(flag_key)
            if handle:
                for cb in handle._listeners:
                    try:
                        cb(event)
                    except Exception:
                        logger.error("Exception in flag-specific on_change listener", exc_info=True)

    def _fire_change_listeners_all(self, source: str) -> None:
        """Fire listeners for all known flags (used after refresh)."""
        for flag_key in self._flag_store:
            self._fire_change_listeners(flag_key, source)

    # ------------------------------------------------------------------
    # Model conversion
    # ------------------------------------------------------------------

    def _to_model(self, parsed: Any) -> Flag:
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> Flag:
        attrs = resource.attributes
        return Flag(
            self,
            id=_unset_to_none(resource.id) or "",
            key=attrs.key,
            name=attrs.name,
            type=attrs.type_,
            default=attrs.default,
            values=_extract_values(attrs.values),
            description=_unset_to_none(attrs.description),
            environments=_extract_environments(attrs.environments),
            created_at=_unset_to_none(getattr(attrs, "created_at", None)),
            updated_at=_unset_to_none(getattr(attrs, "updated_at", None)),
        )


# ---------------------------------------------------------------------------
# AsyncFlagsClient
# ---------------------------------------------------------------------------


class AsyncFlagsClient:
    """Asynchronous flags namespace.  Obtained via ``AsyncSmplClient(...).flags``."""

    def __init__(self, parent: AsyncSmplClient) -> None:
        self._parent = parent
        self._flags_http = AuthenticatedClient(
            base_url=_DEFAULT_FLAGS_BASE_URL,
            token=parent._api_key,
        )
        self._app_http = AuthenticatedClient(
            base_url=_DEFAULT_APP_BASE_URL,
            token=parent._api_key,
        )

        # Runtime state
        self._environment: str | None = None
        self._flag_store: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._cache = _ResolutionCache()
        self._context_provider: Callable[[], list[Context]] | None = None
        self._context_buffer = _ContextRegistrationBuffer()
        self._handles: dict[str, _FlagHandle] = {}
        self._global_listeners: list[Callable[[FlagChangeEvent], None]] = []

        # Shared WebSocket (set during connect)
        self._ws_manager: SharedWebSocket | None = None

    # ------------------------------------------------------------------
    # Management methods (async)
    # ------------------------------------------------------------------

    async def create(
        self,
        key: str,
        *,
        name: str,
        type: FlagType,
        default: Any,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> AsyncFlag:
        """Create a flag."""
        from smplkit.flags.types import FlagType as FT

        if values is None and type == FT.BOOLEAN:
            values = [{"name": "True", "value": True}, {"name": "False", "value": False}]

        gen_flag = _build_gen_flag(
            key=key,
            name=name,
            type_=type.value if isinstance(type, FT) else str(type),
            default=default,
            values=values or [],
            description=description,
        )
        body = _build_request_body(gen_flag)
        try:
            response = await create_flag.asyncio_detailed(client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to create flag")
        return self._to_model(response.parsed)

    async def get(self, flag_id: str) -> AsyncFlag:
        """Fetch a flag by UUID."""
        from uuid import UUID

        try:
            response = await get_flag.asyncio_detailed(UUID(flag_id), client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Flag {flag_id} not found")
        return self._to_model(response.parsed)

    async def list(self) -> list[AsyncFlag]:
        """List all flags."""
        try:
            response = await list_flags.asyncio_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._resource_to_model(r) for r in response.parsed.data]

    async def delete(self, flag_id: str) -> None:
        """Delete a flag by UUID."""
        from uuid import UUID

        try:
            response = await delete_flag.asyncio_detailed(UUID(flag_id), client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    async def _update_flag(
        self,
        *,
        flag: AsyncFlag,
        environments: dict[str, Any] | None = None,
        values: list[dict[str, Any]] | None = None,
        default: Any = None,
        description: str | None = None,
        name: str | None = None,
    ) -> AsyncFlag:
        """Internal: PUT a full flag update."""
        from uuid import UUID

        gen_flag = _build_gen_flag(
            key=flag.key,
            name=name if name is not None else flag.name,
            type_=flag.type,
            default=default if default is not None else flag.default,
            values=values if values is not None else flag.values,
            description=description if description is not None else flag.description,
            environments=environments if environments is not None else flag.environments,
        )
        body = _build_request_body(gen_flag)
        try:
            response = await update_flag.asyncio_detailed(UUID(flag.id), client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to update flag")
        return self._to_model(response.parsed)

    # ------------------------------------------------------------------
    # Context type management (async, direct HTTP)
    # ------------------------------------------------------------------

    async def create_context_type(self, key: str, *, name: str) -> ContextType:
        """Create a context type."""
        resp = await self._app_http.get_async_httpx_client().post(
            "/api/v1/context_types",
            json={"data": {"type": "context_type", "attributes": {"key": key, "name": name}}},
        )
        _check_response_status(resp.status_code, resp.content)
        data = resp.json().get("data", {})
        return self._parse_context_type(data)

    async def update_context_type(self, ct_id: str, *, attributes: dict[str, Any]) -> ContextType:
        """Update a context type (merge attributes)."""
        resp = await self._app_http.get_async_httpx_client().put(
            f"/api/v1/context_types/{ct_id}",
            json={"data": {"type": "context_type", "attributes": {"attributes": attributes}}},
        )
        _check_response_status(resp.status_code, resp.content)
        data = resp.json().get("data", {})
        return self._parse_context_type(data)

    async def list_context_types(self) -> list[ContextType]:
        """List all context types."""
        resp = await self._app_http.get_async_httpx_client().get("/api/v1/context_types")
        _check_response_status(resp.status_code, resp.content)
        items = resp.json().get("data", [])
        return [self._parse_context_type(item) for item in items]

    async def delete_context_type(self, ct_id: str) -> None:
        """Delete a context type."""
        resp = await self._app_http.get_async_httpx_client().delete(f"/api/v1/context_types/{ct_id}")
        _check_response_status(resp.status_code, resp.content)

    async def list_contexts(self, *, context_type_key: str) -> list[dict[str, Any]]:
        """List context instances filtered by context_type_key."""
        params = {"filter[context_type]": context_type_key}
        resp = await self._app_http.get_async_httpx_client().get("/api/v1/contexts", params=params)
        _check_response_status(resp.status_code, resp.content)
        return resp.json().get("data", [])

    # ------------------------------------------------------------------
    # Runtime: typed flag handles
    # ------------------------------------------------------------------

    def boolFlag(self, key: str, default: bool) -> BoolFlagHandle:
        handle = BoolFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    def stringFlag(self, key: str, default: str) -> StringFlagHandle:
        handle = StringFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    def numberFlag(self, key: str, default: int | float) -> NumberFlagHandle:
        handle = NumberFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    def jsonFlag(self, key: str, default: dict[str, Any]) -> JsonFlagHandle:
        handle = JsonFlagHandle(self, key, default)
        self._handles[key] = handle
        return handle

    # ------------------------------------------------------------------
    # Runtime: context provider
    # ------------------------------------------------------------------

    def context_provider(self, fn: Callable[[], list[Context]]) -> Callable[[], list[Context]]:
        """Register a context provider function.  Works as a decorator."""
        self._context_provider = fn
        return fn

    # ------------------------------------------------------------------
    # Runtime: connect / disconnect / refresh
    # ------------------------------------------------------------------

    async def _connect_internal(self) -> None:
        """Connect to the environment: fetch flags, register on shared WebSocket.

        Called by :meth:`AsyncSmplClient.connect`. Uses the environment set on
        the parent client.
        """
        self._environment = self._parent._environment
        await self._fetch_all_flags()
        self._connected = True
        self._cache.clear()

        # Register on the shared WebSocket
        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("flag_changed", self._handle_flag_changed)
        self._ws_manager.on("flag_deleted", self._handle_flag_deleted)

    async def disconnect(self) -> None:
        """Disconnect: unregister from WebSocket, flush contexts, clear state."""
        # Unregister from the shared WebSocket
        if self._ws_manager is not None:
            self._ws_manager.off("flag_changed", self._handle_flag_changed)
            self._ws_manager.off("flag_deleted", self._handle_flag_deleted)
            self._ws_manager = None

        await self._flush_contexts_async()
        self._flag_store.clear()
        self._cache.clear()
        self._connected = False
        self._environment = None

    async def refresh(self) -> None:
        """Re-fetch all flag definitions and clear cache."""
        await self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners_all("manual")

    def connection_status(self) -> str:
        if self._ws_manager is not None:
            return self._ws_manager.connection_status
        return "disconnected"

    def stats(self) -> FlagStats:
        return FlagStats(cache_hits=self._cache.cache_hits, cache_misses=self._cache.cache_misses)

    # ------------------------------------------------------------------
    # Runtime: change listeners
    # ------------------------------------------------------------------

    def on_change(self, callback: Callable[[FlagChangeEvent], None]) -> Callable[[FlagChangeEvent], None]:
        """Register a global change listener.  Works as a decorator."""
        self._global_listeners.append(callback)
        return callback

    # ------------------------------------------------------------------
    # Runtime: context registration
    # ------------------------------------------------------------------

    def register(self, context: Context | list[Context]) -> None:
        """Explicitly register context(s) for background batch registration.

        Accepts a single :class:`Context` or a list.  Queues into the same
        batch buffer used by the automatic context provider side-effect.
        Fire-and-forget — never blocks, never raises on registration failure.

        Works before ``connect()`` is called; contexts are queued locally
        and flushed when the connection is established or
        ``flush_contexts()`` is called.
        """
        if isinstance(context, list):
            self._context_buffer.observe(context)
        else:
            self._context_buffer.observe([context])

    async def flush_contexts(self) -> None:
        """Flush pending context registrations to the server."""
        await self._flush_contexts_async()

    async def _flush_contexts_async(self) -> None:
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            await self._app_http.get_async_httpx_client().put(
                "/api/v1/contexts/bulk",
                json={"contexts": batch},
            )
        except Exception:
            logger.debug("Context registration flush failed", exc_info=True)

    # ------------------------------------------------------------------
    # Runtime: Tier 1 evaluate
    # ------------------------------------------------------------------

    async def evaluate(self, key: str, *, environment: str, context: list[Context]) -> Any:
        """Tier 1 explicit evaluation — stateless, no provider or cache."""
        eval_dict = _contexts_to_eval_dict(context)

        # Auto-inject service context if set and not already provided
        if self._parent._service and "service" not in eval_dict:
            eval_dict["service"] = {"key": self._parent._service}

        if self._connected and key in self._flag_store:
            flag_def = self._flag_store[key]
        else:
            flags = await self._fetch_flags_list()
            flag_def = None
            for f in flags:
                if f.get("key") == key:
                    flag_def = f
                    break
            if flag_def is None:
                return None

        return _evaluate_flag(flag_def, environment, eval_dict)

    # ------------------------------------------------------------------
    # Internal: evaluation
    # ------------------------------------------------------------------

    def _evaluate_handle(self, key: str, default: Any, context: list[Context] | None) -> Any:
        """Core evaluation used by flag handles."""
        if not self._connected:
            raise SmplNotConnectedError("SmplClient is not connected. Call client.connect() first.")

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

        # Auto-inject service context if set and not already provided
        if self._parent._service and "service" not in eval_dict:
            eval_dict["service"] = {"key": self._parent._service}

        ctx_hash = _hash_context(eval_dict)
        cache_key = f"{key}:{ctx_hash}"

        hit, cached_value = self._cache.get(cache_key)
        if hit:
            return cached_value

        flag_def = self._flag_store.get(key)
        if flag_def is None:
            self._cache.put(cache_key, default)
            return default

        value = _evaluate_flag(flag_def, self._environment, eval_dict)
        if value is None:
            value = default

        self._cache.put(cache_key, value)
        return value

    def _flush_contexts_bg(self) -> None:
        """Background sync flush for context registration."""
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            self._flags_http.get_httpx_client().put(
                "/api/v1/contexts/bulk",
                json={"contexts": batch},
            )
        except Exception:
            logger.debug("Context registration flush failed", exc_info=True)

    # ------------------------------------------------------------------
    # Internal: flag store
    # ------------------------------------------------------------------

    async def _fetch_all_flags(self) -> None:
        flags = await self._fetch_flags_list()
        self._flag_store = {f["key"]: f for f in flags}

    async def _fetch_flags_list(self) -> list[dict[str, Any]]:
        try:
            response = await list_flags.asyncio_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        result = []
        for r in response.parsed.data:
            attrs = r.attributes
            result.append(
                {
                    "key": attrs.key,
                    "name": attrs.name,
                    "type": attrs.type_,
                    "default": attrs.default,
                    "values": _extract_values(attrs.values),
                    "description": _unset_to_none(attrs.description),
                    "environments": _extract_environments(attrs.environments),
                }
            )
        return result

    # ------------------------------------------------------------------
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_flag_changed(self, data: dict[str, Any]) -> None:
        """Handle a flag_changed event by re-fetching all flags."""
        flag_key = data.get("key")
        # Re-fetch using sync httpx (called from WS background thread)
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
            if response.parsed and hasattr(response.parsed, "data"):
                new_store: dict[str, dict[str, Any]] = {}
                for r in response.parsed.data:
                    attrs = r.attributes
                    new_store[attrs.key] = {
                        "key": attrs.key,
                        "name": attrs.name,
                        "type": attrs.type_,
                        "default": attrs.default,
                        "values": _extract_values(attrs.values),
                        "description": _unset_to_none(attrs.description),
                        "environments": _extract_environments(attrs.environments),
                    }
                self._flag_store = new_store
        except Exception:
            ws_logger.error("Failed to refresh flags after WS event", exc_info=True)
        self._cache.clear()
        self._fire_change_listeners(flag_key, "websocket")

    def _handle_flag_deleted(self, data: dict[str, Any]) -> None:
        """Handle a flag_deleted event by re-fetching all flags."""
        flag_key = data.get("key")
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
            if response.parsed and hasattr(response.parsed, "data"):
                new_store: dict[str, dict[str, Any]] = {}
                for r in response.parsed.data:
                    attrs = r.attributes
                    new_store[attrs.key] = {
                        "key": attrs.key,
                        "name": attrs.name,
                        "type": attrs.type_,
                        "default": attrs.default,
                        "values": _extract_values(attrs.values),
                        "description": _unset_to_none(attrs.description),
                        "environments": _extract_environments(attrs.environments),
                    }
                self._flag_store = new_store
        except Exception:
            ws_logger.error("Failed to refresh flags after WS event", exc_info=True)
        self._cache.clear()
        self._fire_change_listeners(flag_key, "websocket")

    def _fire_change_listeners(self, flag_key: str | None, source: str) -> None:
        if flag_key:
            event = FlagChangeEvent(key=flag_key, source=source)
            for cb in self._global_listeners:
                try:
                    cb(event)
                except Exception:
                    logger.error("Exception in global flags on_change listener", exc_info=True)
            handle = self._handles.get(flag_key)
            if handle:
                for cb in handle._listeners:
                    try:
                        cb(event)
                    except Exception:
                        logger.error("Exception in flag-specific on_change listener", exc_info=True)

    def _fire_change_listeners_all(self, source: str) -> None:
        for flag_key in self._flag_store:
            self._fire_change_listeners(flag_key, source)

    # ------------------------------------------------------------------
    # Model conversion
    # ------------------------------------------------------------------

    def _to_model(self, parsed: Any) -> AsyncFlag:
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> AsyncFlag:
        attrs = resource.attributes
        return AsyncFlag(
            self,
            id=_unset_to_none(resource.id) or "",
            key=attrs.key,
            name=attrs.name,
            type=attrs.type_,
            default=attrs.default,
            values=_extract_values(attrs.values),
            description=_unset_to_none(attrs.description),
            environments=_extract_environments(attrs.environments),
            created_at=_unset_to_none(getattr(attrs, "created_at", None)),
            updated_at=_unset_to_none(getattr(attrs, "updated_at", None)),
        )

    # ------------------------------------------------------------------
    # Shared helper for context type parsing
    # ------------------------------------------------------------------

    def _parse_context_type(self, data: dict[str, Any]) -> ContextType:
        attrs = data.get("attributes", {})
        return ContextType(
            id=data.get("id", ""),
            key=attrs.get("key", ""),
            name=attrs.get("name", ""),
            attributes=attrs.get("attributes") or {},
        )


# Also add the method to the sync client
FlagsClient._parse_context_type = AsyncFlagsClient._parse_context_type  # type: ignore[attr-defined]


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
            logger.debug("JSON Logic evaluation error for rule %r", rule, exc_info=True)
            continue

    return fallback
