"""Shared context-registration buffer.

Used by both the public ``client.management.contexts.register()`` path
AND the flags client's internal auto-registration during flag eval.
A single buffer per SmplClient keeps the dedupe LRU honest and means
the flags-eval observation flow doesn't have to know about the
management-plane API at all.
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
    """Thread-safe batch buffer for context registration.

    Observed contexts are deduped against an LRU and queued for flush.
    A single shared buffer is owned by the SmplClient and used by both
    the management-plane public API and the flags-internal eval path.
    """

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
