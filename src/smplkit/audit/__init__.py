"""Smpl Audit SDK namespace — fire-and-forget event recording.

ADR-047. The audit subsystem records who did what to which resource and
when; the SDK exposes ``client.audit.events.create(...)`` for write,
``client.audit.events.list(...)`` for paginated read, and
``client.audit.events.get(id)`` for single retrieval.

Writes default to fire-and-forget — the call enqueues the event onto an
in-memory bounded buffer and returns immediately. A background worker
thread flushes the buffer on a periodic tick or whenever the buffer
exceeds its high-water mark. Reads are synchronous.
"""

from smplkit.audit.client import AsyncAuditClient, AuditClient
from smplkit.audit.models import Event

__all__ = ["AsyncAuditClient", "AuditClient", "Event"]
