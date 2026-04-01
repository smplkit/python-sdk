"""Config runtime — resolved, cached configuration for a specific environment.

The :class:`ConfigRuntime` is the primary read-path object.  All value-access
methods are synchronous dict reads with zero network overhead.  It is created
by :meth:`Config.connect` / :meth:`AsyncConfig.connect`, which eagerly fetch
the full parent chain and resolve values before returning.

A shared WebSocket connection (managed by :class:`SharedWebSocket`) receives
real-time change notifications from the app service, updates the local cache,
and fires registered listeners — all without blocking the calling thread.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from smplkit._resolver import resolve

if TYPE_CHECKING:
    from smplkit._ws import SharedWebSocket

logger = logging.getLogger("smplkit")
ws_logger = logging.getLogger("smplkit.config.ws")


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
        return f"ConfigStats(fetch_count={self.fetch_count}, last_fetch_at={self.last_fetch_at!r})"


class ConfigRuntime:
    """Resolved, locally-cached configuration for a single config + environment.

    All value-access methods (:meth:`get`, :meth:`get_str`, etc.) are
    **synchronous** — they read from an in-process dict and never touch the
    network.  The runtime is constructed by :meth:`Config.connect` /
    :meth:`AsyncConfig.connect`.

    A shared WebSocket connection receives real-time change notifications.
    If the WebSocket connection fails, the runtime continues to serve
    cached values.

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
        ws_manager: SharedWebSocket | None = None,
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

        self._ws_manager = ws_manager

        # Register on the shared WebSocket
        if self._ws_manager is not None:
            self._ws_manager.on("config_changed", self._handle_config_changed)
            self._ws_manager.on("config_deleted", self._handle_config_deleted)

    # ------------------------------------------------------------------
    # Event handlers (called by SharedWebSocket)
    # ------------------------------------------------------------------

    def _handle_config_changed(self, data: dict[str, Any]) -> None:
        """Handle a config_changed event by re-fetching and re-resolving."""
        config_id = data.get("config_id")
        # Check if this config is in our chain
        if config_id not in [entry.get("id") for entry in self._chain]:
            return  # Not our config

        self._refresh_from_server(source="websocket")

    def _handle_config_deleted(self, data: dict[str, Any]) -> None:
        """Handle a config_deleted notification."""
        deleted_id = data.get("config_id")
        # Check if this is one of our configs
        if deleted_id not in [entry.get("id") for entry in self._chain]:
            return
        ws_logger.warning("Watched config %s was deleted.", deleted_id)
        self._deleted = True
        self._closed = True

    def _refresh_from_server(self, *, source: str = "websocket") -> None:
        """Re-fetch the full chain via HTTP and re-resolve.

        Called on config_changed events and after reconnection.
        """
        if self._fetch_chain_fn is None:
            ws_logger.debug("No fetch_chain_fn provided, skipping refresh")
            return

        try:
            result = self._fetch_chain_fn()
            if asyncio.iscoroutine(result):
                # Should not happen from WS handler, but handle gracefully
                ws_logger.debug("fetch_chain_fn returned coroutine in sync context, skipping")
                return
            new_chain = result
            self._chain = new_chain
            new_cache = resolve(new_chain, self._environment)
            self._fetch_count += len(new_chain)
            self._last_fetch_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

            with self._cache_lock:
                old_cache = self._cache
                self._cache = new_cache

            self._fire_change_listeners(old_cache, new_cache, source=source)
        except Exception:
            ws_logger.error("Failed to refresh config from server", exc_info=True)

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
            ws_logger.warning("Accessing config after deletion — returning stale cached values")
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
        if self._ws_manager is not None:
            return self._ws_manager.connection_status
        return "disconnected"

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
        self._last_fetch_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._cache_lock:
            old_cache = self._cache
            self._cache = new_cache

        self._fire_change_listeners(old_cache, new_cache, source="manual")
        ws_logger.info("Manual refresh completed for %s", self._config_key)

    async def close(self) -> None:
        """Close the runtime connection.

        Unregisters event handlers from the shared WebSocket.
        """
        self._closed = True

        # Unregister from the shared WebSocket
        if self._ws_manager is not None:
            self._ws_manager.off("config_changed", self._handle_config_changed)
            self._ws_manager.off("config_deleted", self._handle_config_deleted)

        ws_logger.debug("ConfigRuntime closed (config_key=%s)", self._config_key)

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    def __enter__(self) -> ConfigRuntime:
        return self

    def __exit__(self, *args: Any) -> None:
        self._closed = True
        if self._ws_manager is not None:
            self._ws_manager.off("config_changed", self._handle_config_changed)
            self._ws_manager.off("config_deleted", self._handle_config_deleted)
        ws_logger.debug("ConfigRuntime closed (config_key=%s)", self._config_key)

    async def __aenter__(self) -> ConfigRuntime:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        loaded = bool(self._cache)
        return f"ConfigRuntime(config_key={self._config_key!r}, environment={self._environment!r}, loaded={loaded})"
