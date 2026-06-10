"""Smpl Audit SDK namespace.

ADR-047. The audit subsystem records who did what to which resource and
when. Audit installs no in-process machinery, so it has no
runtime/management split: a single :class:`AuditClient` (sync) /
:class:`AsyncAuditClient` (async) exposes the full surface and is
reachable as ``client.audit`` on :class:`smplkit.SmplClient` or
constructed directly via :class:`AuditClient`.

The client owns event recording and read-side queries plus SIEM forwarder
CRUD:

* ``audit.events.record(..., flush=False)`` — enqueue an audit event for
  asynchronous delivery; pass ``flush=True`` to block until the buffer drains.
* ``audit.events.flush(timeout=...)`` — drain the buffer.
* ``audit.events.list(...)`` / ``audit.events.get(id)`` — query the audit log.
* ``audit.resource_types.list(...)``, ``audit.event_types.list(...)``, and
  ``audit.categories.list(...)`` — distinct-value listings that back the
  Activity tab filter dropdowns.
* ``audit.forwarders.new/get/list/save/delete`` — manage SIEM forwarders.

The shared dataclasses (``Event``, ``Forwarder``, ``AsyncForwarder``,
``HttpConfiguration``, ``HttpHeader``, ``ResourceType``, ``EventType``,
``Category``) plus the ``ForwarderType``, ``HttpMethod``, and
``TransformType`` enums live in :mod:`smplkit.audit.models` and are
re-exported here for convenience.
"""

from smplkit.audit.models import (
    AsyncForwarder,
    Category,
    Event,
    EventType,
    Forwarder,
    ForwarderEnvironment,
    ForwarderType,
    HttpConfiguration,
    HttpHeader,
    HttpMethod,
    ResourceType,
    TransformType,
)

__all__ = [
    "AsyncForwarder",
    "Category",
    "Event",
    "EventType",
    "Forwarder",
    "ForwarderEnvironment",
    "ForwarderType",
    "HttpConfiguration",
    "HttpHeader",
    "HttpMethod",
    "ResourceType",
    "TransformType",
]
