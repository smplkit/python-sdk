"""StdlibLoggingAdapter — bridges smplkit logging runtime to Python stdlib logging."""

from __future__ import annotations

import logging as stdlib_logging
from collections.abc import Callable

from smplkit.logging.adapters.base import LoggingAdapter


class StdlibLoggingAdapter(LoggingAdapter):
    """Adapter for Python's built-in :mod:`logging` module.

    Discovers existing loggers, intercepts new logger creation for
    continuous discovery, and applies log levels at runtime.
    """

    def __init__(
        self,
        *,
        prefix: str | None = None,
        discover_existing: bool = True,
    ) -> None:
        self._prefix = prefix
        self._discover_existing = discover_existing
        self._original_getLogger: Callable | None = None

    @property
    def name(self) -> str:
        return "stdlib-logging"

    def discover(self) -> list[tuple[str, int]]:
        if not self._discover_existing:
            return []
        loggers: list[tuple[str, int]] = []
        root = stdlib_logging.getLogger()
        if self._prefix is None:
            loggers.append(("root", root.getEffectiveLevel()))
        for name, obj in stdlib_logging.root.manager.loggerDict.items():
            if isinstance(obj, stdlib_logging.Logger):
                if self._prefix is not None and not name.startswith(self._prefix):
                    continue
                loggers.append((name, obj.getEffectiveLevel()))
        return loggers

    def apply_level(self, logger_name: str, level: int) -> None:
        stdlib_logging.getLogger(logger_name).setLevel(level)

    def install_hook(self, on_new_logger: Callable[[str, int], None]) -> None:
        if self._original_getLogger is not None:
            return  # Already patched

        self._original_getLogger = stdlib_logging.Manager.getLogger
        original = self._original_getLogger
        prefix = self._prefix

        def _patched_getLogger(self_mgr, name):  # type: ignore[no-untyped-def]
            is_new = name not in self_mgr.loggerDict
            logger = original(self_mgr, name)  # type: ignore[misc]
            if is_new and isinstance(logger, stdlib_logging.Logger):
                if prefix is None or name.startswith(prefix):
                    on_new_logger(name, logger.getEffectiveLevel())
            return logger

        stdlib_logging.Manager.getLogger = _patched_getLogger  # type: ignore[assignment]

    def uninstall_hook(self) -> None:
        if self._original_getLogger is not None:
            stdlib_logging.Manager.getLogger = self._original_getLogger  # type: ignore[assignment]
            self._original_getLogger = None
