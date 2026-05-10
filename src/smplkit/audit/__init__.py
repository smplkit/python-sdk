"""Smpl Audit SDK runtime namespace — fire-and-forget event recording.

ADR-047. The audit subsystem records who did what to which resource and
when; this module exposes the runtime surface only:

* ``client.audit.events.record(..., flush=False)`` — enqueue an audit
  event for asynchronous delivery; pass ``flush=True`` to block until
  the buffer drains.
* ``client.audit.events.flush(timeout=...)`` — drain the buffer.

Every other audit operation (query, listings, forwarder CRUD,
test_forwarder, wipe) lives on :class:`smplkit.SmplManagementClient`
under ``mgmt.audit.*``. See ``smplkit.management.audit``.

The shared dataclasses (``Event``, ``Forwarder``, ``ForwarderHttp``,
``HttpHeader``, ``ForwarderDelivery``, ``ResourceType``, ``Action``,
``WipeResult``, ``RetryFailedDeliveriesSummary``,
``TestForwarderResult``) live in :mod:`smplkit.audit.models` and are
re-exported here for convenience — both the runtime and the management
clients return them.
"""

from smplkit.audit.client import AsyncAuditClient, AuditClient
from smplkit.audit.models import (
    Action,
    Event,
    Forwarder,
    ForwarderDelivery,
    ForwarderHttp,
    ForwarderType,
    HttpHeader,
    ResourceType,
    RetryFailedDeliveriesSummary,
    TestForwarderResult,
    WipeResult,
)

__all__ = [
    "Action",
    "AsyncAuditClient",
    "AuditClient",
    "Event",
    "Forwarder",
    "ForwarderDelivery",
    "ForwarderHttp",
    "ForwarderType",
    "HttpHeader",
    "ResourceType",
    "RetryFailedDeliveriesSummary",
    "TestForwarderResult",
    "WipeResult",
]
