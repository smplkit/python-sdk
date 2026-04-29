"""Logger registration buffer — used by the runtime LoggingClient."""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any


class _LoggerRegistrationBuffer:
    """Batches discovered loggers for bulk registration."""

    def __init__(self) -> None:
        self._seen: OrderedDict[str, str] = OrderedDict()  # normalized_id → resolved_level
        self._pending: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(
        self,
        normalized_id: str,
        smpl_level: str | None,
        smpl_resolved_level: str,
        service: str | None,
        environment: str | None,
    ) -> None:
        """Queue a logger for registration if not already seen.

        Args:
            normalized_id: Normalized logger name.
            smpl_level: Explicit smplkit level string, or None if the logger
                inherits its level from a parent.
            smpl_resolved_level: Effective smplkit level string (always non-None).
            service: Service name to include in the payload, or None.
            environment: Environment name to include in the payload, or None.
        """
        with self._lock:
            if normalized_id not in self._seen:
                self._seen[normalized_id] = smpl_resolved_level
                item: dict[str, Any] = {"id": normalized_id, "resolved_level": smpl_resolved_level}
                if smpl_level is not None:
                    item["level"] = smpl_level
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
