"""Auto-discovery of Python loggers via stdlib introspection and monkey-patching."""

from __future__ import annotations

import logging as stdlib_logging
from collections.abc import Callable

_original_getLogger: Callable | None = None


def discover_existing_loggers() -> list[tuple[str, int]]:
    """Scan the stdlib logging registry for all existing loggers.

    Returns a list of ``(name, effective_level)`` tuples.
    PlaceHolder objects (created by intermediate names) are skipped.
    """
    loggers: list[tuple[str, int]] = []
    root = stdlib_logging.getLogger()
    loggers.append(("root", root.getEffectiveLevel()))
    for name, obj in stdlib_logging.root.manager.loggerDict.items():
        if isinstance(obj, stdlib_logging.Logger):
            loggers.append((name, obj.getEffectiveLevel()))
    return loggers


def install_discovery_patch(on_new_logger: Callable[[str, int], None]) -> None:
    """Monkey-patch ``logging.Manager.getLogger`` to detect new loggers."""
    global _original_getLogger
    if _original_getLogger is not None:
        return  # Already patched

    _original_getLogger = stdlib_logging.Manager.getLogger

    def _patched_getLogger(self, name):  # type: ignore[no-untyped-def]
        is_new = name not in self.loggerDict
        logger = _original_getLogger(self, name)  # type: ignore[misc]
        if is_new and isinstance(logger, stdlib_logging.Logger):
            on_new_logger(name, logger.getEffectiveLevel())
        return logger

    stdlib_logging.Manager.getLogger = _patched_getLogger  # type: ignore[assignment]


def uninstall_discovery_patch() -> None:
    """Restore the original ``getLogger``. Called on client close."""
    global _original_getLogger
    if _original_getLogger is not None:
        stdlib_logging.Manager.getLogger = _original_getLogger  # type: ignore[assignment]
        _original_getLogger = None
