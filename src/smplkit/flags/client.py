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
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
    _raise_for_status,
)
from smplkit._helpers import key_to_display_name
from smplkit._generated.app.api.contexts import (
    bulk_register_contexts as gen_bulk_register_contexts,
)
from smplkit._generated.app.models.context_bulk_item import ContextBulkItem
from smplkit._generated.app.models.context_bulk_item_attributes import ContextBulkItemAttributes
from smplkit._generated.app.models.context_bulk_register import ContextBulkRegister
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
_CONTEXT_REGISTRATION_LRU_SIZE = 10_000
_CONTEXT_BATCH_FLUSH_SIZE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_response_status(status_code: Any, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions with full JSON:API error detail."""
    _raise_for_status(int(status_code), content)


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


def _extract_values(values: Any) -> list[dict[str, Any]] | None:
    """Extract a list of FlagValue to plain dicts, or None for unconstrained."""
    if values is None:
        return None
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
    name: str,
    type_: str,
    default: Any,
    values: list[dict[str, Any]] | None,
    description: str | None = None,
    environments: dict[str, Any] | None = None,
) -> GenFlag:
    """Build a generated Flag model from plain values."""
    gen_values: list[GenFlagValue] | None = None
    if values is not None:
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
        name=name,
        type_=type_,
        default=default,
        values=gen_values,
        description=description,
        environments=gen_envs,
    )


def _build_request_body(gen_flag: GenFlag, *, flag_id: str | None = None) -> ResponseFlag:
    """Wrap a generated Flag in the JSON:API request envelope.

    The server's Flag schema declares ``id`` as a *writeOnly* attribute (used
    as the slug on create).  The generated Python model omits writeOnly fields,
    so we inject it via ``additional_properties``.
    """
    if flag_id is not None:
        gen_flag["id"] = flag_id
    resource = ResourceFlag(attributes=gen_flag, id=flag_id, type_="flag")
    return ResponseFlag(data=resource)


def _flag_dict_from_json(data: dict[str, Any]) -> dict[str, Any]:
    """Extract flat flag attributes from a JSON:API response ``data`` block."""
    attrs = data["attributes"]
    values_raw = attrs.get("values")
    values: list[dict[str, Any]] | None = None
    if values_raw is not None:
        values = [{"name": v["name"], "value": v["value"]} for v in values_raw]
    envs: dict[str, Any] = {}
    for env_key, env_data in (attrs.get("environments") or {}).items():
        envs[env_key] = {
            "enabled": env_data.get("enabled", False),
            "default": env_data.get("default"),
            "rules": env_data.get("rules", []),
        }
    return {
        "id": data.get("id", ""),
        "name": attrs["name"],
        "type": attrs["type"],
        "default": attrs["default"],
        "values": values,
        "description": attrs.get("description"),
        "environments": envs,
        "created_at": attrs.get("created_at"),
        "updated_at": attrs.get("updated_at"),
    }


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

    def __init__(self, *, id: str, source: str) -> None:
        self.id = id
        self.source = source

    def __repr__(self) -> str:
        return f"FlagChangeEvent(id={self.id!r}, source={self.source!r})"


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
        self._handles: dict[str, Flag] = {}
        self._global_listeners: list[Callable[[FlagChangeEvent], None]] = []
        self._key_listeners: dict[str, list[Callable[[FlagChangeEvent], None]]] = {}

        # Shared WebSocket (set during connect)
        self._ws_manager: SharedWebSocket | None = None

    # ------------------------------------------------------------------
    # Management: factory methods (return unsaved Flag with created_at=None)
    # ------------------------------------------------------------------

    def newBooleanFlag(
        self,
        id: str,
        *,
        default: bool,
        name: str | None = None,
        description: str | None = None,
    ) -> BooleanFlag:
        """Create an unsaved boolean flag .  Call ``.save()`` to persist."""
        return BooleanFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="BOOLEAN",
            default=default,
            values=[{"name": "True", "value": True}, {"name": "False", "value": False}],
            description=description,
        )

    def newStringFlag(
        self,
        id: str,
        *,
        default: str,
        name: str | None = None,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> StringFlag:
        """Create an unsaved string flag .  Call ``.save()`` to persist."""
        return StringFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="STRING",
            default=default,
            values=values,
            description=description,
        )

    def newNumberFlag(
        self,
        id: str,
        *,
        default: int | float,
        name: str | None = None,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> NumberFlag:
        """Create an unsaved numeric flag .  Call ``.save()`` to persist."""
        return NumberFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="NUMERIC",
            default=default,
            values=values,
            description=description,
        )

    def newJsonFlag(
        self,
        id: str,
        *,
        default: dict[str, Any],
        name: str | None = None,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> JsonFlag:
        """Create an unsaved JSON flag .  Call ``.save()`` to persist."""
        return JsonFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="JSON",
            default=default,
            values=values,
            description=description,
        )

    # ------------------------------------------------------------------
    # Management: CRUD
    # ------------------------------------------------------------------

    def get(self, id: str) -> Flag:
        """Fetch a flag by id."""
        try:
            response = get_flag.sync_detailed(id, client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        return self._model_from_json(body["data"])

    def list(self) -> list[Flag]:
        """List all flags."""
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        return [self._model_from_json(r) for r in body.get("data", [])]

    def delete(self, id: str) -> None:
        """Delete a flag by id."""
        try:
            response = delete_flag.sync_detailed(id, client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    def _create_flag(self, flag: Flag) -> Flag:
        """Internal: POST a new flag.  Called by Flag.save() when created_at is None."""
        gen_flag = _build_gen_flag(
            name=flag.name,
            type_=flag.type,
            default=flag.default,
            values=flag.values,
            description=flag.description,
            environments=flag.environments or None,
        )
        body = _build_request_body(gen_flag, flag_id=flag.id)
        try:
            response = create_flag.sync_detailed(client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        resp_body = json.loads(response.content)
        return self._model_from_json(resp_body["data"])

    def _update_flag(self, *, flag: Flag) -> Flag:
        """Internal: PUT a full flag update.  Called by Flag.save() when created_at is set."""
        gen_flag = _build_gen_flag(
            name=flag.name,
            type_=flag.type,
            default=flag.default,
            values=flag.values,
            description=flag.description,
            environments=flag.environments or None,
        )
        body = _build_request_body(gen_flag, flag_id=flag.id)
        try:
            response = update_flag.sync_detailed(flag.id, client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        resp_body = json.loads(response.content)
        return self._model_from_json(resp_body["data"])

    # ------------------------------------------------------------------
    # Runtime: typed flag handles
    # ------------------------------------------------------------------

    def booleanFlag(self, id: str, *, default: bool) -> BooleanFlag:
        """Declare a boolean flag handle for runtime evaluation."""
        handle = BooleanFlag(self, id=id, name=id, type="BOOLEAN", default=default)
        self._handles[id] = handle
        return handle

    def stringFlag(self, id: str, *, default: str) -> StringFlag:
        """Declare a string flag handle for runtime evaluation."""
        handle = StringFlag(self, id=id, name=id, type="STRING", default=default)
        self._handles[id] = handle
        return handle

    def numberFlag(self, id: str, *, default: int | float) -> NumberFlag:
        """Declare a numeric flag handle for runtime evaluation."""
        handle = NumberFlag(self, id=id, name=id, type="NUMERIC", default=default)
        self._handles[id] = handle
        return handle

    def jsonFlag(self, id: str, *, default: dict[str, Any]) -> JsonFlag:
        """Declare a JSON flag handle for runtime evaluation."""
        handle = JsonFlag(self, id=id, name=id, type="JSON", default=default)
        self._handles[id] = handle
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
        self._fetch_all_flags()
        self._connected = True
        self._cache.clear()

        # Register on the shared WebSocket
        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("flag_changed", self._handle_flag_changed)
        self._ws_manager.on("flag_deleted", self._handle_flag_deleted)

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
    # Runtime: context registration
    # ------------------------------------------------------------------

    def register(self, context: Context | list[Context]) -> None:
        """Explicitly register context(s) for background batch registration."""
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
            body = _build_bulk_register_body(batch)
            gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        except Exception:
            logger.debug("Context registration flush failed", exc_info=True)

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
        flag_id = data.get("id")
        self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners(flag_id, "websocket")

    def _handle_flag_deleted(self, data: dict[str, Any]) -> None:
        flag_id = data.get("id")
        self._fetch_all_flags()
        self._cache.clear()
        self._fire_change_listeners(flag_id, "websocket")

    # ------------------------------------------------------------------
    # Internal: flag store
    # ------------------------------------------------------------------

    def _fetch_all_flags(self) -> None:
        flags = self._fetch_flags_list()
        self._flag_store = {f["id"]: f for f in flags}

    def _fetch_flags_list(self) -> list[dict[str, Any]]:
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
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

    def _fire_change_listeners(self, flag_id: str | None, source: str) -> None:
        if flag_id:
            event = FlagChangeEvent(id=flag_id, source=source)
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
            name=attrs.name,
            type=attrs.type_,
            default=attrs.default,
            values=_extract_values(attrs.values),
            description=_unset_to_none(attrs.description),
            environments=_extract_environments(attrs.environments),
            created_at=_unset_to_none(getattr(attrs, "created_at", None)),
            updated_at=_unset_to_none(getattr(attrs, "updated_at", None)),
        )

    def _model_from_json(self, data: dict[str, Any]) -> Flag:
        """Build a Flag from a raw JSON:API resource dict (handles null values)."""
        d = _flag_dict_from_json(data)
        return Flag(self, **d)


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
        self._handles: dict[str, AsyncFlag] = {}
        self._global_listeners: list[Callable[[FlagChangeEvent], None]] = []
        self._key_listeners: dict[str, list[Callable[[FlagChangeEvent], None]]] = {}

        # Shared WebSocket (set during connect)
        self._ws_manager: SharedWebSocket | None = None

    # ------------------------------------------------------------------
    # Management: factory methods (return unsaved AsyncFlag with created_at=None)
    # ------------------------------------------------------------------

    def newBooleanFlag(
        self,
        id: str,
        *,
        default: bool,
        name: str | None = None,
        description: str | None = None,
    ) -> AsyncBooleanFlag:
        return AsyncBooleanFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="BOOLEAN",
            default=default,
            values=[{"name": "True", "value": True}, {"name": "False", "value": False}],
            description=description,
        )

    def newStringFlag(
        self,
        id: str,
        *,
        default: str,
        name: str | None = None,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> AsyncStringFlag:
        return AsyncStringFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="STRING",
            default=default,
            values=values,
            description=description,
        )

    def newNumberFlag(
        self,
        id: str,
        *,
        default: int | float,
        name: str | None = None,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> AsyncNumberFlag:
        return AsyncNumberFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="NUMERIC",
            default=default,
            values=values,
            description=description,
        )

    def newJsonFlag(
        self,
        id: str,
        *,
        default: dict[str, Any],
        name: str | None = None,
        description: str | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> AsyncJsonFlag:
        return AsyncJsonFlag(
            self,
            id=id,
            name=name or key_to_display_name(id),
            type="JSON",
            default=default,
            values=values,
            description=description,
        )

    # ------------------------------------------------------------------
    # Management: CRUD (async)
    # ------------------------------------------------------------------

    async def get(self, id: str) -> AsyncFlag:
        """Fetch a flag by id."""
        try:
            response = await get_flag.asyncio_detailed(id, client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        return self._model_from_json(body["data"])

    async def list(self) -> list[AsyncFlag]:
        """List all flags."""
        try:
            response = await list_flags.asyncio_detailed(client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        body = json.loads(response.content)
        return [self._model_from_json(r) for r in body.get("data", [])]

    async def delete(self, id: str) -> None:
        """Delete a flag by id."""
        try:
            response = await delete_flag.asyncio_detailed(id, client=self._flags_http)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    async def _create_flag(self, flag: AsyncFlag) -> AsyncFlag:
        """Internal: POST a new flag."""
        gen_flag = _build_gen_flag(
            name=flag.name,
            type_=flag.type,
            default=flag.default,
            values=flag.values,
            description=flag.description,
            environments=flag.environments or None,
        )
        body = _build_request_body(gen_flag, flag_id=flag.id)
        try:
            response = await create_flag.asyncio_detailed(client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        resp_body = json.loads(response.content)
        return self._model_from_json(resp_body["data"])

    async def _update_flag(self, *, flag: AsyncFlag) -> AsyncFlag:
        """Internal: PUT a full flag update."""
        gen_flag = _build_gen_flag(
            name=flag.name,
            type_=flag.type,
            default=flag.default,
            values=flag.values,
            description=flag.description,
            environments=flag.environments or None,
        )
        body = _build_request_body(gen_flag, flag_id=flag.id)
        try:
            response = await update_flag.asyncio_detailed(flag.id, client=self._flags_http, body=body)
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        resp_body = json.loads(response.content)
        return self._model_from_json(resp_body["data"])

    # ------------------------------------------------------------------
    # Runtime: typed flag handles
    # ------------------------------------------------------------------

    def booleanFlag(self, id: str, *, default: bool) -> AsyncBooleanFlag:
        handle = AsyncBooleanFlag(self, id=id, name=id, type="BOOLEAN", default=default)
        self._handles[id] = handle
        return handle

    def stringFlag(self, id: str, *, default: str) -> AsyncStringFlag:
        handle = AsyncStringFlag(self, id=id, name=id, type="STRING", default=default)
        self._handles[id] = handle
        return handle

    def numberFlag(self, id: str, *, default: int | float) -> AsyncNumberFlag:
        handle = AsyncNumberFlag(self, id=id, name=id, type="NUMERIC", default=default)
        self._handles[id] = handle
        return handle

    def jsonFlag(self, id: str, *, default: dict[str, Any]) -> AsyncJsonFlag:
        handle = AsyncJsonFlag(self, id=id, name=id, type="JSON", default=default)
        self._handles[id] = handle
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
        await self._fetch_all_flags()
        self._connected = True
        self._cache.clear()

        self._ws_manager = self._parent._ensure_ws()
        self._ws_manager.on("flag_changed", self._handle_flag_changed)
        self._ws_manager.on("flag_deleted", self._handle_flag_deleted)

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
    # Runtime: context registration
    # ------------------------------------------------------------------

    def register(self, context: Context | list[Context]) -> None:
        if isinstance(context, list):
            self._context_buffer.observe(context)
        else:
            self._context_buffer.observe([context])

    async def flush_contexts(self) -> None:
        await self._flush_contexts_async()

    async def _flush_contexts_async(self) -> None:
        batch = self._context_buffer.drain()
        if not batch:
            return
        try:
            body = _build_bulk_register_body(batch)
            await gen_bulk_register_contexts.asyncio_detailed(client=self._app_http, body=body)
        except Exception:
            logger.debug("Context registration flush failed", exc_info=True)

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
            self._fetch_all_flags_sync()
            self._connected = True
            self._cache.clear()
            self._ws_manager = self._parent._ensure_ws()
            self._ws_manager.on("flag_changed", self._handle_flag_changed)
            self._ws_manager.on("flag_deleted", self._handle_flag_deleted)

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
            logger.debug("Context registration flush failed", exc_info=True)

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
            _maybe_reraise_network_error(exc)
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
            _maybe_reraise_network_error(exc)
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

    # ------------------------------------------------------------------
    # Internal: event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_flag_changed(self, data: dict[str, Any]) -> None:
        flag_id = data.get("id")
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
            _check_response_status(response.status_code, response.content)
            body = json.loads(response.content)
            new_store: dict[str, dict[str, Any]] = {}
            for r in body.get("data", []):
                d = _flag_dict_from_json(r)
                new_store[d["id"]] = {
                    "id": d["id"],
                    "name": d["name"],
                    "type": d["type"],
                    "default": d["default"],
                    "values": d["values"],
                    "description": d["description"],
                    "environments": d["environments"],
                }
            self._flag_store = new_store
        except Exception:
            ws_logger.error("Failed to refresh flags after WS event", exc_info=True)
        self._cache.clear()
        self._fire_change_listeners(flag_id, "websocket")

    def _handle_flag_deleted(self, data: dict[str, Any]) -> None:
        flag_id = data.get("id")
        try:
            response = list_flags.sync_detailed(client=self._flags_http)
            _check_response_status(response.status_code, response.content)
            body = json.loads(response.content)
            new_store: dict[str, dict[str, Any]] = {}
            for r in body.get("data", []):
                d = _flag_dict_from_json(r)
                new_store[d["id"]] = {
                    "id": d["id"],
                    "name": d["name"],
                    "type": d["type"],
                    "default": d["default"],
                    "values": d["values"],
                    "description": d["description"],
                    "environments": d["environments"],
                }
            self._flag_store = new_store
        except Exception:
            ws_logger.error("Failed to refresh flags after WS event", exc_info=True)
        self._cache.clear()
        self._fire_change_listeners(flag_id, "websocket")

    def _fire_change_listeners(self, flag_id: str | None, source: str) -> None:
        if flag_id:
            event = FlagChangeEvent(id=flag_id, source=source)
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
            name=attrs.name,
            type=attrs.type_,
            default=attrs.default,
            values=_extract_values(attrs.values),
            description=_unset_to_none(attrs.description),
            environments=_extract_environments(attrs.environments),
            created_at=_unset_to_none(getattr(attrs, "created_at", None)),
            updated_at=_unset_to_none(getattr(attrs, "updated_at", None)),
        )

    def _model_from_json(self, data: dict[str, Any]) -> AsyncFlag:
        """Build an AsyncFlag from a raw JSON:API resource dict (handles null values)."""
        d = _flag_dict_from_json(data)
        return AsyncFlag(self, **d)


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
            logger.debug("JSON Logic evaluation error for rule %r", rule, exc_info=True)
            continue

    return fallback
