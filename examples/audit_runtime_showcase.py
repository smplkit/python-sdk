"""
Demonstrates the smplkit runtime SDK for Smpl Audit.

Audit is a fire-and-forget event-recording surface. ``create`` enqueues
the event onto an in-memory bounded buffer and returns immediately;
a background thread retries with exponential backoff on transient
failures and drops oldest under back pressure (ADR-047 §2.6).
Reads (``get``, ``list``) are synchronous on the wire.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/audit_runtime_showcase.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

from smplkit import AsyncSmplClient


async def main() -> None:

    # create the client (use SmplClient for synchronous use)
    async with AsyncSmplClient(
        environment="production", service="showcase-service"
    ) as client:

        # unique resource id so we can find back exactly the events this
        # showcase wrote, regardless of what other history exists.
        resource_id = f"showcase-{uuid.uuid4().hex[:8]}"

        # 1) fire-and-forget create — returns immediately. The actual POST
        #    happens on a background thread. customer events must NOT use
        #    a resource_type beginning with "smpl." (reserved for smplkit-
        #    emitted events; the server returns 403).
        client.audit.events.create(
            action="invoice.created",
            resource_type="invoice",
            resource_id=resource_id,
            occurred_at=datetime.now(timezone.utc),
            snapshot={"total_cents": 4900, "currency": "USD"},
            data={"request_id": "req-abc"},
        )

        # 2) caller-supplied idempotency key — replaying with the same
        #    key returns the original event (the server dedupes on
        #    account_id + idempotency_key).
        idempotency_key = f"showcase-{uuid.uuid4().hex}"
        client.audit.events.create(
            action="invoice.updated",
            resource_type="invoice",
            resource_id=resource_id,
            snapshot={"total_cents": 5400},
            idempotency_key=idempotency_key,
        )
        # safe replay — same key, same event id server-side.
        client.audit.events.create(
            action="invoice.updated",
            resource_type="invoice",
            resource_id=resource_id,
            snapshot={"total_cents": 5400},
            idempotency_key=idempotency_key,
        )

        # 3) flush — block until the in-memory buffer drains so that
        #    the events we just wrote are durable before we read them.
        client.audit.events.flush(timeout=5.0)

        # 4) list — server-side filters per ADR-047 §4. Cursor pagination
        #    via page_size / page_after; page.next_cursor is non-None
        #    when more pages exist.
        page = client.audit.events.list(
            resource_type="invoice",
            resource_id=resource_id,
            page_size=10,
        )
        print(f"Found {len(page.events)} events for {resource_id}:")
        for event in page.events:
            print(f"  {event.action}  id={event.id}  actor={event.actor_type}")

        # idempotency dedupe check — we issued 3 creates (1 distinct +
        # 2 with the same idempotency key) so we expect exactly 2 events.
        assert len(page.events) == 2, (
            f"Expected 2 events (idempotency dedup), got {len(page.events)}"
        )

        # 5) get — read a single event by id.
        first = client.audit.events.get(page.events[0].id)
        print(f"Round-tripped: {first.action} at {first.occurred_at}")

        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
