"""
Demonstrates the smplkit runtime SDK for Smpl Audit.

Covers: event record / list / get, plus the SIEM forwarders surface
(create / list / delete + the test_forwarder/execute proxy + a
do_not_forward event flow).

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The Pro tier is required for the forwarders portion. The showcase
      gracefully skips those steps on a 402 (free/standard tier) so it
      stays runnable in any environment.

Usage::

    python examples/audit_runtime_showcase.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

from smplkit import AsyncSmplClient
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit.audit import ForwarderHttp, HttpHeader


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
            data={
                "snapshot": {"total_cents": 4900, "currency": "USD"},
                "request_id": "req-abc",
            },
        )

        # force the event to be posted (normally happens automatically, in the
        # background, but we want to force it to be written now for this demo)
        client.audit.events.flush(timeout=2.0)

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

        # ----------------------------------------------------------------
        # Forwarders (Pro tier — gracefully skip on 402)
        # ----------------------------------------------------------------
        try:
            fwd = client.audit.forwarders.create(
                name=f"showcase-{uuid.uuid4().hex[:6]}",
                forwarder_type="http",
                http=ForwarderHttp(
                    method="POST",
                    url="https://httpbin.org/post",
                    headers=[HttpHeader(name="X-Showcase", value="ok")],
                    success_status="2xx",
                ),
            )
        except UnexpectedStatus as exc:
            if exc.status_code == 402:
                print("Skipping forwarder showcase — account is not Pro tier")
                print("Done!")
                return
            raise

        print(f"Created forwarder: {fwd.slug}")
        try:
            # do_not_forward suppresses the forward but still records the
            # skip in the delivery log.
            client.audit.events.record(
                action="invoice.created",
                resource_type="invoice",
                resource_id=f"{some_resource_id}-skipped",
                do_not_forward=True,
            )
            client.audit.events.flush(timeout=2.0)

            # Test the destination via the proxy.
            test = client.audit.functions.test_forwarder.actions.execute(
                url="https://httpbin.org/post",
                body='{"hello":"world"}',
                success_status="2xx",
                timeout_ms=5000,
            )
            print(
                f"test_forwarder: succeeded={test.succeeded} status={test.response_status}"
            )

            listed = client.audit.forwarders.list(page_size=5)
            print(f"Account has {len(listed.forwarders)} active forwarders")
        finally:
            client.audit.forwarders.delete(fwd.id)
            print(f"Deleted forwarder: {fwd.slug}")

        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
