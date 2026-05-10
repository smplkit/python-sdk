"""
Demonstrates the smplkit RUNTIME SDK for Smpl Audit.

The runtime client is for fire-and-forget event recording in app code.
Every other audit-service operation (query, distinct-value listings,
forwarder CRUD, the test_forwarder action, the wipe action) lives on
the management client — see ``audit_management_showcase.py``.

What this showcases:

- ``client.audit.events.record(...)`` — enqueue events asynchronously.
- ``client.audit.events.record(..., flush=True)`` — record and flush
  in a single call when the caller needs the event durable before
  continuing (CLI tools, in-test assertions, processes about to exit).
- ``client.audit.events.flush(timeout=...)`` — drain the buffer when
  several fire-and-forget records need to land before the next step.

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
    async with AsyncSmplClient(
        environment="production", service="showcase-service"
    ) as client:
        some_resource_id = f"showcase-{uuid.uuid4().hex[:8]}"

        # 1) Default fire-and-forget — record returns immediately and the
        #    buffer's worker thread retries with exponential backoff in the
        #    background. This is the right choice on a request-handling
        #    hot path where the calling thread shouldn't wait on the POST.
        client.audit.events.record(
            action="invoice.created",
            resource_type="invoice",
            resource_id=some_resource_id,
            occurred_at=datetime.now(timezone.utc),
            data={
                "snapshot": {"total_cents": 4900, "currency": "USD"},
                "request_id": "req-abc",
            },
        )

        # 2) Several fire-and-forget records, then a single flush at the
        #    end. Useful when you have a small batch and want them all
        #    durable before continuing to the next step.
        for i in range(3):
            client.audit.events.record(
                action="invoice.line_added",
                resource_type="invoice",
                resource_id=some_resource_id,
                data={"line": {"sku": f"sku-{i}", "qty": 1}},
            )
        client.audit.events.flush(timeout=2.0)

        # 3) ``flush=True`` is the single-call equivalent — record AND
        #    flush in one go. Useful for CLI tools, end-of-process events,
        #    and any flow where the next line shouldn't run until the
        #    record has been confirmed durable.
        client.audit.events.record(
            action="invoice.finalized",
            resource_type="invoice",
            resource_id=some_resource_id,
            data={"snapshot": {"status": "finalized"}},
            flush=True,
        )

        print(f"Recorded events for invoice {some_resource_id}")
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
