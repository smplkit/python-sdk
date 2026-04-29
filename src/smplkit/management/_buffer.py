"""Registration buffers owned by ``SmplManagementClient`` sub-clients.

Three buffers, each lives on a management sub-client:

- :class:`_ContextRegistrationBuffer`  →  ``mgmt.contexts._buffer``
- :class:`_FlagRegistrationBuffer`     →  ``mgmt.flags._buffer``
- :class:`_LoggerRegistrationBuffer`   →  ``mgmt.loggers._buffer``

The runtime client (``SmplClient``) reaches into these buffers via
``client.manage.<resource>._observe(...)`` so there is exactly one
buffer + one bulk-flush implementation per resource.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from smplkit.flags.types import Context

# When the deduplication LRU exceeds this size, the oldest entry is
# evicted. The next observation of an evicted entry will re-flush.
_CONTEXT_REGISTRATION_LRU_SIZE = 10_000


class _ContextRegistrationBuffer:
    """Thread-safe batch buffer for context registration."""

    def __init__(self) -> None:
        self._seen: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._pending: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def observe(self, contexts: list[Context]) -> None:
        """Queue any unseen contexts."""
        with self._lock:
            for ctx in contexts:
                cache_key = (ctx.type, ctx.key)
                if cache_key not in self._seen:
                    if len(self._seen) >= _CONTEXT_REGISTRATION_LRU_SIZE:
                        self._seen.popitem(last=False)
                    self._seen[cache_key] = ctx.attributes
                    self._pending.append(
                        {
                            "type": ctx.type,
                            "key": ctx.key,
                            "attributes": dict(ctx.attributes),
                        }
                    )

    def drain(self) -> list[dict[str, Any]]:
        """Return and clear the current pending batch."""
        with self._lock:
            batch = list(self._pending)
            self._pending.clear()
            return batch

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)


class _FlagRegistrationBuffer:
    """Thread-safe batch buffer for flag declarations."""

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
        """Queue a flag declaration for registration if not already seen."""
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


class _LoggerRegistrationBuffer:
    """Thread-safe batch buffer for logger discovery."""

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
        """Queue a discovered logger if not already seen."""
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
