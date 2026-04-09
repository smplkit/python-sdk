"""Abstract base class for pluggable logging framework adapters."""

from __future__ import annotations

import abc
from typing import Callable


class LoggingAdapter(abc.ABC):
    """Contract for pluggable logging framework integration.

    Adapters bridge the smplkit logging runtime to a specific logging framework.
    The core LoggingClient delegates all framework-specific work through this interface.

    Adapters are NOT responsible for: key normalization, caching, bulk registration,
    level resolution, or WebSocket handling. Those remain in the core client.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable adapter name for diagnostics (e.g., 'stdlib-logging')."""

    @abc.abstractmethod
    def discover(self) -> list[tuple[str, int]]:
        """Scan the runtime for existing loggers.

        Returns a list of (logger_name, python_numeric_level) tuples.
        The core client handles normalization of names after receiving them.
        """

    @abc.abstractmethod
    def apply_level(self, logger_name: str, level: int) -> None:
        """Set the level on a specific logger.

        Args:
            logger_name: The original (non-normalized) logger name.
            level: Python numeric level (e.g., 10=DEBUG, 20=INFO, 30=WARNING).
        """

    @abc.abstractmethod
    def install_hook(self, on_new_logger: Callable[[str, int], None]) -> None:
        """Install continuous discovery hook.

        The callback receives (original_name, python_numeric_level) whenever
        a new logger is created in the framework. The core client handles
        normalization and registration.

        May be a no-op if the framework doesn't support creation interception.
        """

    @abc.abstractmethod
    def uninstall_hook(self) -> None:
        """Remove the hook installed by install_hook(). Called on client close()."""
