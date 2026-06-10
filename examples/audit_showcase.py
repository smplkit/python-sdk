"""
Demonstrates the smplkit SDK for Smpl Audit.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/audit_showcase.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

from smplkit import AsyncSmplClient, NotFoundError
from smplkit.audit import (
    ForwarderType,
    HttpConfiguration,
    HttpHeader,
    HttpMethod,
    TransformType,
)


# JSON Logic filter — only forward ``invoice.*`` actions. Events that don't
# match the filter aren't forwarded (and produce no delivery record).
# See https://jsonlogic.com for the full operator reference.
INVOICE_FILTER = {"in": ["invoice.", {"var": "action"}]}

# JSONata template — reshape the event payload before POSTing to the
# destination. This example flattens the event into a compact SIEM-style
# record. See https://jsonata.org for the full language reference.
SIEM_TRANSFORM = """
{
    "event": action,
    "subject": resource_type & ":" & resource_id,
    "ts": occurred_at,
    "actor": actor_label
}
"""

# A forwarder delivers events in an environment only when that environment is
# enabled in its ``environments`` map. The environment must exist and be
# managed for the account.
ENVIRONMENT = "production"


async def main() -> None:

    # or SmplClient for synchronous use
    async with AsyncSmplClient(environment="production") as client:
        audit = client.audit
        some_resource_id = f"showcase-{uuid.uuid4().hex[:8]}"

        # ----- Events: record / list / get --------------------------------

        # record an event with full customer-supplied actor attribution
        await audit.events.record(
            event_type="invoice.created",
            resource_type="invoice",
            resource_id=some_resource_id,
            occurred_at=datetime.now(timezone.utc),
            actor_type="USER",
            actor_id="billing-bot:42",
            actor_label="finance@example.com",
            # An optional free-form bucket label — groups related events and
            # powers the categories discovery listing shown below.
            category="billing",
            data={
                "snapshot": {"total_cents": 4900, "currency": "USD"},
                "request_id": "req-abc",
            },
            flush=True,  # or omit to have events flushed asynchronously
        )
        print(f"Recorded event for invoice {some_resource_id}")

        # list events
        page = await audit.events.list(
            resource_type="invoice", resource_id=some_resource_id
        )
        assert some_resource_id in {e.resource_id for e in page.events}
        recorded_event_id = page.events[0].id
        print(f"Listed {len(page)} event(s) for invoice {some_resource_id}")

        # fetch an event
        event = await audit.events.get(recorded_event_id)
        assert event.id == recorded_event_id
        assert event.resource_id == some_resource_id
        assert event.event_type == "invoice.created"
        assert event.actor_id == "billing-bot:42"
        assert event.actor_label == "finance@example.com"
        assert event.category == "billing"
        # The event is scoped to the environment the client is configured for.
        # The SDK resolves this from the ``X-Smplkit-Environment`` header — the
        # recording call never carries it in the request body.
        assert event.environment == ENVIRONMENT
        print(
            f"Fetched event {event.id}: {event.event_type} "
            f"by {event.actor_label} in {event.environment}"
        )

        # ----- Discovery: distinct resource_types / event_types / categories

        resource_types = await audit.resource_types.list()
        assert "invoice" in {rt.id for rt in resource_types}
        print(f"Observed resource types: {[rt.id for rt in resource_types]}")

        event_types = await audit.event_types.list()
        assert "invoice.created" in {et.id for et in event_types}
        print(f"Observed event types: {[et.id for et in event_types]}")

        categories = await audit.categories.list()
        assert "billing" in {c.id for c in categories}
        print(f"Observed categories: {[c.id for c in categories]}")

        # ----- Forwarders: SIEM streaming CRUD ----------------------------

        forwarder_id = f"showcase-{uuid.uuid4().hex[:6]}"
        try:
            # create a forwarder, enabled in our target environment, with a
            # JSON Logic filter and a JSONata transform. Enablement is
            # per-environment: a forwarder delivers in an environment only
            # when ``environments[env].enabled`` is True.
            forwarder = audit.forwarders.new(
                forwarder_id,
                forwarder_type=ForwarderType.HTTP,
                configuration=HttpConfiguration(
                    method=HttpMethod.POST,
                    url="https://httpbin.org/post",
                    headers=[HttpHeader(name="X-Showcase", value="ok")],
                ),
                environments={ENVIRONMENT: {"enabled": True}},
                filter=INVOICE_FILTER,
                transform=SIEM_TRANSFORM,
                transform_type=TransformType.JSONATA,
            )
            await forwarder.save()
            print(f"Created forwarder: {forwarder.name} (id={forwarder.id})")

            # list forwarders
            listed = await audit.forwarders.list()
            assert forwarder.id in {f.id for f in listed.forwarders}
            print(f"Account has {len(listed.forwarders)} forwarder(s)")

            # get a forwarder, then disable it in our environment via
            # get-mutate-put
            fetched = await audit.forwarders.get(forwarder.id)
            assert fetched.environments[ENVIRONMENT].enabled is True
            fetched.environments[ENVIRONMENT].enabled = False
            await fetched.save()
            assert fetched.environments[ENVIRONMENT].enabled is False
            print(f"Disabled forwarder in {ENVIRONMENT}: {fetched.name}")

            # delete a forwarder
            await fetched.delete()
            remaining = await audit.forwarders.list()
            assert forwarder_id not in {f.id for f in remaining.forwarders}
            print(f"Deleted forwarder: {fetched.name}")
        finally:
            # tear-down: never leave the showcase forwarder behind, even on failure
            try:
                await audit.forwarders.delete(forwarder_id)
            except NotFoundError:
                pass

        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
