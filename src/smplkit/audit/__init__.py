"""Smpl Audit SDK namespace — fire-and-forget event recording plus
SIEM-streaming forwarder management.

ADR-047. The audit subsystem records who did what to which resource and
when; the SDK exposes:

* ``client.audit.events.*`` — record / list / get audit events.
* ``client.audit.forwarders.*`` — manage SIEM forwarders, list and
  retry deliveries (Pro tier only — lower tiers get 402).
* ``client.audit.functions.test_forwarder.actions.execute(...)`` — a
  server-side proxy for previewing a destination configuration without
  the browser hitting CORS. SSRF-guarded.

Writes via ``events.record(...)`` default to fire-and-forget — the call
enqueues the event onto an in-memory bounded buffer and returns
immediately. A background worker thread flushes the buffer on a
periodic tick or whenever the buffer exceeds its high-water mark. Reads
and forwarder management are synchronous.
"""

from smplkit.audit.client import (
    AsyncAuditClient,
    AuditClient,
    DeliveryListPage,
    EventListPage,
    ForwarderListPage,
)
from smplkit.audit.models import (
    Event,
    Forwarder,
    ForwarderDelivery,
    ForwarderHttp,
    HttpHeader,
    RetryFailedDeliveriesSummary,
    TestForwarderResult,
)

__all__ = [
    "AsyncAuditClient",
    "AuditClient",
    "DeliveryListPage",
    "Event",
    "EventListPage",
    "Forwarder",
    "ForwarderDelivery",
    "ForwarderHttp",
    "ForwarderListPage",
    "HttpHeader",
    "RetryFailedDeliveriesSummary",
    "TestForwarderResult",
]
