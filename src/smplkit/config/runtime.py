"""Config runtime — resolved, cached configuration for a specific environment.

The :class:`ConfigRuntime` is the primary read-path object.  All value-access
methods are synchronous dict reads with zero network overhead.  It is created
by :meth:`Config.connect` / :meth:`AsyncConfig.connect`, which eagerly fetch
the full parent chain and resolve values before returning.

A background WebSocket connection receives real-time change notifications
from the config service, updates the local cache, and fires registered
listeners — all without blocking the calling thread.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

import websockets
import websockets.asyncio.client

from smplkit._resolver import resolve

logger = logging.getLogger("smplkit")
ws_logger = logging.getLogger("smplkit.config.ws")

_BACKOFF_SCHEDULE = [1, 2, 4, 8, 16, 32, 60]


class ConfigChangeEvent:
    """Describes a single value change pushed by the server.

    Attributes:
        key: The config key that changed.
        old_value: The previous value.
        new_value: The updated value.
        source: How the change was delivered (``"websocket"``, ``"poll"``,
            or ``"manual"``).
    """

    def __init__(
        self,
        *,
        key: str,
        old_value: Any,
        new_value: Any,
        source: str,
    ) -> None:
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source

    def __repr__(self) -> str:
        return (
            f"ConfigChangeEvent(key={self.key!r}, old_value={self.old_value!r}, "
            f"new_value={self.new_value!r}, source={self.source!r})"
        )


class ConfigStats:
    """Diagnostic statistics for a :class:`ConfigRuntime` instance.

    Attributes:
        fetch_count: Total number of HTTP fetches performed, including
            initial connect and any reconnection re-syncs or manual refreshes.
        last_fetch_at: ISO-8601 timestamp of the most recent fetch, or
            ``None`` if no fetch has occurred.
    """

    def __init__(
        self,
        *,
        fetch_count: int,
        last_fetch_at: str | None,
    ) -> None:
        self.fetch_count = fetch_count
        self.last_fetch_at = last_fetch_at

    def __repr__(self) -> str:
        return (
            f"ConfigStats(fetch_count={self.fetch_count}, "
            f"last_fetch_at={self.last_fetch_at!r})"
        )


class ConfigRuntime:
    """Resolved, locally-cached configuration for a single config + environment.

    All value-access methods (:meth:`get`, :meth:`get_str`, etc.) are
    **synchronous** — they read from an in-process dict and never touch the
    network.  The runtime is constructed by :meth:`Config.connect` /
    :meth:`AsyncConfig.connect`.

    A background daemon thread maintains a WebSocket connection to the config
    service for real-time cache updates.  If the WebSocket connection fails,
    the runtime continues to serve cached values.

    The runtime supports both ``with`` and ``async with`` context managers
    for convenient lifecycle management.

    Raises:
        SmplConnectionError: If a network request fails during
            :meth:`~Config.connect`.
        SmplTimeoutError: If the initial fetch exceeds the *timeout*
            passed to :meth:`~Config.connect`.
    """

    def __init__(
        self,
        *,
        config_key: str,
        config_id: str,
        environment: str,
        chain: list[dict[str, Any]],
        api_key: str,
        base_url: str,
        fetch_chain_fn: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._config_key = config_key
        self._config_id = config_id
        self._environment = environment
        self._chain = [dict(entry) for entry in chain]
        self._api_key = api_key
        self._base_url = base_url
        self._fetch_chain_fn = fetch_chain_fn

        self._cache_lock = threading.Lock()
        self._cache: dict[str, Any] = resolve(chain, environment)
        self._fetch_count = len(chain)
        self._last_fetch_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None]] = []
        self._closed = False
        self._deleted = False
        self._access_after_delete_warned = False

        self._connection_status: str = "disconnected"
        self._ws: Any = None
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._ws_thread: threading.Thread | None = None

        self._start_ws_thread()

    # ------------------------------------------------------------------
    # WebSocket background thread
    # ------------------------------------------------------------------

    def _start_ws_thread(self) -> None:
        """Start the background daemon thread for the WebSocket connection."""
        thread = threading.Thread(
            target=self._ws_thread_entry,
            name=f"smplkit-ws-{self._config_key}",
            daemon=True,
        )
        self._ws_thread = thread
        thread.start()

    def _ws_thread_entry(self) -> None:
        """Entry point for the WebSocket background thread."""
        loop = asyncio.new_event_loop()
        self._ws_loop = loop
        try:
            loop.run_until_complete(self._ws_main())
        except Exception:
            ws_logger.error("WebSocket thread exited unexpectedly", exc_info=True)
        finally:
            # Cancel all remaining tasks (e.g. websockets keepalive) before
            # closing the loop so they don't leak "Task was destroyed" warnings.
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()

    async def _ws_main(self) -> None:
        """Main async routine: connect, subscribe, and enter the receive loop."""
        try:
            await self._connect_and_subscribe()
        except Exception:
            ws_logger.warning(
                "WebSocket connection failed on startup for %s, "
                "operating in cache-only mode",
                self._config_key,
                exc_info=True,
            )
            await self._reconnect()

    def _build_ws_url(self) -> str:
        """Construct the WebSocket URL from the REST base URL."""
        url = self._base_url
        if url.startswith("https://"):
            ws_url = "wss://" + url[len("https://"):]
        elif url.startswith("http://"):
            ws_url = "ws://" + url[len("http://"):]
        else:
            ws_url = "wss://" + url
        ws_url = ws_url.rstrip("/")
        return f"{ws_url}/api/ws/v1/configs?api_key={self._api_key}"

    async def _connect_and_subscribe(self) -> None:
        """Open a WebSocket, send subscribe, wait for confirmation."""
        url = self._build_ws_url()
        self._connection_status = "connecting"
        ws_logger.debug("Connecting to WebSocket: %s", url.split("?")[0])

        self._ws = await websockets.asyncio.client.connect(url)
        ws_logger.debug("WebSocket connected")

        subscribe_msg = json.dumps({
            "type": "subscribe",
            "config_id": self._config_id,
            "environment": self._environment,
        })
        await self._ws.send(subscribe_msg)
        ws_logger.debug("Subscription sent for config_id=%s env=%s",
                        self._config_id, self._environment)

        # Wait for subscribed confirmation
        raw = await self._ws.recv()
        data = json.loads(raw)
        if data.get("type") == "error":
            raise RuntimeError(f"Subscription error: {data.get('message')}")
        if data.get("type") == "subscribed":
            ws_logger.debug("Subscription confirmed")

        self._connection_status = "connected"
        await self._ws_receive_loop()

    async def _ws_receive_loop(self) -> None:
        """Process incoming WebSocket messages until closed."""
        while not self._closed:
            try:
                raw = await self._ws.recv()
                data = json.loads(raw)
                msg_type = data.get("type")
                ws_logger.debug("Received message type=%s", msg_type)

                if msg_type == "config_changed":
                    self._handle_config_changed(data)
                elif msg_type == "config_deleted":
                    self._handle_config_deleted(data)
            except websockets.ConnectionClosed as exc:
                if self._closed:
                    break
                close_code = exc.rcvd.code if exc.rcvd else None
                close_reason = exc.rcvd.reason if exc.rcvd else ""
                if close_code == 1000 and "deleted" in close_reason.lower():
                    break
                ws_logger.warning(
                    "WebSocket closed (code=%s), reconnecting...", close_code
                )
                self._connection_status = "connecting"
                await self._reconnect()
                break
            except Exception:
                if self._closed:
                    break
                ws_logger.error(
                    "Unexpected error in WebSocket receive loop", exc_info=True
                )
                self._connection_status = "connecting"
                await self._reconnect()
                break

    def _handle_config_changed(self, data: dict[str, Any]) -> None:
        """Apply a config_changed message to the local chain and cache.

        This performs ZERO network calls. The entire update is local:
        1. Apply changes to the matching chain entry.
        2. Re-resolve the full configuration.
        3. Diff old vs new resolved cache.
        4. Swap the cache.
        5. Fire listeners for changed keys.
        """
        changed_config_id = data.get("config_id")
        changes = data.get("changes", [])
        if not changes:
            return

        # Find the chain entry that was mutated
        chain_entry = None
        for entry in self._chain:
            if entry.get("id") == changed_config_id:
                chain_entry = entry
                break

        if chain_entry is None:
            ws_logger.warning(
                "Received config_changed for unknown config_id=%s",
                changed_config_id,
            )
            return

        # Apply changes to the chain entry. The server sends changes already
        # filtered for this environment. We apply to both base and env-specific
        # values so that re-resolve produces the correct result regardless of
        # where the original value came from.
        base_values = chain_entry.get("values") or {}
        environments = chain_entry.get("environments") or {}
        env_data = environments.get(self._environment, {})
        env_values = (env_data.get("values") if isinstance(env_data, dict) else None) or {}

        for change in changes:
            key = change.get("key")
            new_value = change.get("new_value")
            old_value = change.get("old_value")

            if new_value is None and old_value is not None:
                # Key removed — remove from both
                base_values.pop(key, None)
                env_values.pop(key, None)
            else:
                # Key added or changed — update in both base and env values
                # so re-resolve picks up the new value regardless of layer
                base_values[key] = new_value
                env_values[key] = new_value

        chain_entry["values"] = base_values
        if self._environment in environments:
            environments[self._environment]["values"] = env_values
        elif env_values:
            environments[self._environment] = {"values": env_values}
        chain_entry["environments"] = environments

        # Re-resolve the full configuration
        new_cache = resolve(self._chain, self._environment)

        # Swap cache and diff
        with self._cache_lock:
            old_cache = self._cache
            self._cache = new_cache

        # Fire listeners for changed keys (outside the lock)
        self._fire_change_listeners(old_cache, new_cache, source="websocket")

    def _handle_config_deleted(self, data: dict[str, Any]) -> None:
        """Handle a config_deleted notification."""
        deleted_id = data.get("config_id")
        ws_logger.warning("Watched config %s was deleted.", deleted_id)
        self._deleted = True
        self._closed = True
        self._connection_status = "disconnected"

    def _fire_change_listeners(
        self,
        old_cache: dict[str, Any],
        new_cache: dict[str, Any],
        *,
        source: str,
    ) -> None:
        """Diff two caches and fire listeners for any changed keys."""
        all_keys = set(old_cache.keys()) | set(new_cache.keys())
        fired = 0
        for key in all_keys:
            old_val = old_cache.get(key)
            new_val = new_cache.get(key)
            if old_val == new_val:
                continue

            event = ConfigChangeEvent(
                key=key,
                old_value=old_val,
                new_value=new_val,
                source=source,
            )
            for callback, key_filter in self._listeners:
                if key_filter is not None and key_filter != key:
                    continue
                try:
                    callback(event)
                    fired += 1
                except Exception:
                    ws_logger.error(
                        "Exception in on_change listener for key %r",
                        key,
                        exc_info=True,
                    )

        if fired:
            ws_logger.debug("Fired %d listener callbacks", fired)

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff, then re-sync cache."""
        attempt = 0
        while not self._closed:
            delay = _BACKOFF_SCHEDULE[min(attempt, len(_BACKOFF_SCHEDULE) - 1)]
            ws_logger.info(
                "Reconnecting in %d seconds (attempt %d)...",
                delay,
                attempt + 1,
            )
            await asyncio.sleep(delay)
            if self._closed:
                return
            try:
                await self._connect_and_subscribe()
                await self._resync_cache()
                ws_logger.info("Reconnected successfully.")
                return
            except Exception:
                ws_logger.warning("Reconnect attempt %d failed.", attempt + 1)
                attempt += 1

    async def _resync_cache(self) -> None:
        """Re-fetch the full chain via HTTP and re-resolve.

        This is called after reconnection to catch changes missed while
        disconnected.
        """
        if self._fetch_chain_fn is None:
            ws_logger.debug("No fetch_chain_fn provided, skipping resync")
            return

        try:
            new_chain = self._fetch_chain_fn()
            self._chain = new_chain
            new_cache = resolve(new_chain, self._environment)
            self._fetch_count += len(new_chain)
            self._last_fetch_at = (
                datetime.datetime.now(datetime.timezone.utc).isoformat()
            )

            with self._cache_lock:
                old_cache = self._cache
                self._cache = new_cache

            self._fire_change_listeners(old_cache, new_cache, source="websocket")
        except Exception:
            ws_logger.error("Failed to resync cache after reconnect", exc_info=True)

    # ------------------------------------------------------------------
    # Value access (all synchronous, thread-safe)
    # ------------------------------------------------------------------

    def get(self, key: str, *, default: Any = None) -> Any:
        """Return the resolved value for *key*, or *default* if absent.

        Args:
            key: The config key to look up.
            default: Value to return when *key* is not present.

        Returns:
            The resolved value, or *default*.
        """
        if self._deleted and not self._access_after_delete_warned:
            ws_logger.warning(
                "Accessing config after deletion — returning stale cached values"
            )
            self._access_after_delete_warned = True
        with self._cache_lock:
            return self._cache.get(key, default)

    def get_str(self, key: str, *, default: str | None = None) -> str | None:
        """Return the value for *key* if it is a :class:`str`, else *default*.

        Args:
            key: The config key to look up.
            default: Fallback when *key* is absent or not a string.

        Returns:
            The string value, or *default*.
        """
        with self._cache_lock:
            value = self._cache.get(key)
        return value if isinstance(value, str) else default

    def get_int(self, key: str, *, default: int | None = None) -> int | None:
        """Return the value for *key* if it is an :class:`int`, else *default*.

        Args:
            key: The config key to look up.
            default: Fallback when *key* is absent or not an int.

        Returns:
            The int value, or *default*.
        """
        with self._cache_lock:
            value = self._cache.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def get_bool(self, key: str, *, default: bool | None = None) -> bool | None:
        """Return the value for *key* if it is a :class:`bool`, else *default*.

        Args:
            key: The config key to look up.
            default: Fallback when *key* is absent or not a bool.

        Returns:
            The bool value, or *default*.
        """
        with self._cache_lock:
            value = self._cache.get(key)
        return value if isinstance(value, bool) else default

    def get_all(self) -> dict[str, Any]:
        """Return a shallow copy of the full resolved configuration.

        Returns:
            A new dict containing all resolved key/value pairs.
        """
        with self._cache_lock:
            return dict(self._cache)

    def exists(self, key: str) -> bool:
        """Check whether *key* is present in the resolved configuration.

        Args:
            key: The config key to check.

        Returns:
            ``True`` if the key exists, ``False`` otherwise.
        """
        with self._cache_lock:
            return key in self._cache

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def on_change(
        self,
        callback: Callable[[ConfigChangeEvent], None],
        *,
        key: str | None = None,
    ) -> None:
        """Register a listener that fires when a config value changes.

        Args:
            callback: Called with a :class:`ConfigChangeEvent` when a change
                is detected.
            key: If provided, the listener fires only for changes to this
                specific key. If ``None``, the listener fires for all changes.
        """
        self._listeners.append((callback, key))

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def stats(self) -> ConfigStats:
        """Return diagnostic statistics for this runtime.

        Returns:
            A :class:`ConfigStats` snapshot.
        """
        return ConfigStats(
            fetch_count=self._fetch_count,
            last_fetch_at=self._last_fetch_at,
        )

    def connection_status(self) -> str:
        """Return the current WebSocket connection status.

        Returns:
            ``"connected"`` if the WebSocket is open, ``"connecting"`` if
            reconnecting, or ``"disconnected"`` if closed or never connected.
        """
        return self._connection_status

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def refresh(self) -> None:
        """Force a manual refresh of the cached configuration.

        Fetches the full config chain via HTTP, re-resolves values,
        updates the local cache, and fires listeners for any changes
        with ``source="manual"``.

        Raises:
            SmplConnectionError: If the HTTP fetch fails.
        """
        if self._fetch_chain_fn is None:
            ws_logger.debug("No fetch_chain_fn provided, cannot refresh")
            return

        result = self._fetch_chain_fn()
        if asyncio.iscoroutine(result):
            new_chain = await result
        else:
            new_chain = result
        self._chain = new_chain
        new_cache = resolve(new_chain, self._environment)
        self._fetch_count += len(new_chain)
        self._last_fetch_at = (
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

        with self._cache_lock:
            old_cache = self._cache
            self._cache = new_cache

        self._fire_change_listeners(old_cache, new_cache, source="manual")
        ws_logger.info("Manual refresh completed for %s", self._config_key)

    async def close(self) -> None:
        """Close the runtime connection.

        Shuts down the WebSocket connection and waits for the background
        thread to exit.
        """
        self._closed = True
        self._connection_status = "disconnected"

        # The WebSocket lives on the background thread's event loop, so we
        # must close it there — not on the caller's loop.
        if self._ws is not None and self._ws_loop is not None:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._ws.close(), self._ws_loop
                )
                future.result(timeout=2.0)
            except Exception:
                pass

        # Wait for background thread to exit
        if self._ws_thread is not None and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=2.0)

        ws_logger.debug("ConfigRuntime closed (config_key=%s)", self._config_key)

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    def __enter__(self) -> ConfigRuntime:
        return self

    def __exit__(self, *args: Any) -> None:
        self._closed = True
        self._connection_status = "disconnected"
        if self._ws_loop is not None and self._ws is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._ws.close(), self._ws_loop
                )
            except Exception:
                pass
        if self._ws_thread is not None and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=2.0)
        ws_logger.debug("ConfigRuntime closed (config_key=%s)", self._config_key)

    async def __aenter__(self) -> ConfigRuntime:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        loaded = bool(self._cache)
        return (
            f"ConfigRuntime(config_key={self._config_key!r}, "
            f"environment={self._environment!r}, loaded={loaded})"
        )
