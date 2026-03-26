"""Config runtime — resolved, cached configuration for a specific environment.

The :class:`ConfigRuntime` is the primary read-path object.  All value-access
methods are synchronous dict reads with zero network overhead.  It is created
by :meth:`Config.connect` / :meth:`AsyncConfig.connect`, which eagerly fetch
the full parent chain and resolve values before returning.
"""

from __future__ import annotations

import datetime
import logging
from collections.abc import Callable
from typing import Any

from smplkit._resolver import resolve

logger = logging.getLogger("smplkit")


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
        fetch_count: Total number of HTTP fetches performed during
            :meth:`~Config.connect`.
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
        environment: str,
        chain: list[dict[str, Any]],
    ) -> None:
        self._config_key = config_key
        self._environment = environment
        self._chain = chain
        self._cache: dict[str, Any] = resolve(chain, environment)
        self._fetch_count = len(chain)
        self._last_fetch_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._listeners: list[tuple[Callable[[ConfigChangeEvent], None], str | None]] = []
        self._closed = False

        logger.debug(
            "WebSocket not yet available, operating in cache-only mode"
        )

    # ------------------------------------------------------------------
    # Value access (all synchronous)
    # ------------------------------------------------------------------

    def get(self, key: str, *, default: Any = None) -> Any:
        """Return the resolved value for *key*, or *default* if absent.

        Args:
            key: The config key to look up.
            default: Value to return when *key* is not present.

        Returns:
            The resolved value, or *default*.
        """
        return self._cache.get(key, default)

    def get_str(self, key: str, *, default: str | None = None) -> str | None:
        """Return the value for *key* if it is a :class:`str`, else *default*.

        Args:
            key: The config key to look up.
            default: Fallback when *key* is absent or not a string.

        Returns:
            The string value, or *default*.
        """
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
        value = self._cache.get(key)
        return value if isinstance(value, bool) else default

    def get_all(self) -> dict[str, Any]:
        """Return a shallow copy of the full resolved configuration.

        Returns:
            A new dict containing all resolved key/value pairs.
        """
        return dict(self._cache)

    def exists(self, key: str) -> bool:
        """Check whether *key* is present in the resolved configuration.

        Args:
            key: The config key to check.

        Returns:
            ``True`` if the key exists, ``False`` otherwise.
        """
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
            ``"disconnected"`` — WebSocket is not yet implemented.
        """
        return "disconnected"

    # ------------------------------------------------------------------
    # Lifecycle (stubs — WebSocket not yet implemented)
    # ------------------------------------------------------------------

    async def refresh(self) -> None:
        """Force a manual refresh of the cached configuration.

        Raises:
            NotImplementedError: WebSocket is not yet implemented.
        """
        raise NotImplementedError("WebSocket not yet implemented")

    async def close(self) -> None:
        """Close the runtime connection.

        Tears down the WebSocket connection when implemented. Currently
        sets a closed flag and logs a debug message.
        """
        self._closed = True
        logger.debug("ConfigRuntime closed (config_key=%s)", self._config_key)

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    def __enter__(self) -> ConfigRuntime:
        return self

    def __exit__(self, *args: Any) -> None:
        self._closed = True
        logger.debug("ConfigRuntime closed (config_key=%s)", self._config_key)

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
