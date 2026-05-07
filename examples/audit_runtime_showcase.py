"""
Demonstrates the smplkit runtime SDK for Smpl Audit.

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

        # record an event
        some_resource_id = f"showcase-{uuid.uuid4().hex[:8]}"
        client.audit.events.record(
            action="invoice.created",
            resource_type="invoice",
            resource_id=some_resource_id,
            occurred_at=datetime.now(timezone.utc),
            snapshot={"total_cents": 4900, "currency": "USD"},
            data={"request_id": "req-abc"},
        )

        # force the event to be posted (normally happens automatically, in the
        # background, but we want to force it to be written now for this demo)
        client.audit.events.flush(timeout=5.0)

        # list events
        page = client.audit.events.list(
            resource_type="invoice",
            resource_id=some_resource_id,
            page_size=10,
        )
        print(f"Found {len(page.events)} events for {some_resource_id}:")
        for event in page.events:
            print(f"  {event.action}  id={event.id}  actor={event.actor_type}")

        assert len(page.events) == 1, (
            f"Expected 1 event, got {len(page.events)}"
        )

        # fetch an event by ID
        first = client.audit.events.get(page.events[0].id)
        print(f"Round-tripped: {first.action} at {first.occurred_at}")

        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
