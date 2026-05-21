"""
Demonstrates the smplkit runtime SDK for Smpl Config.

The canonical runtime pattern is ``get_or_create``: declare each
configuration from code with in-code defaults, then use typed getters
to read values. The SDK registers every declaration with smplkit so
the admin sees what configs and keys your service uses and can
override them per environment without a code change.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/config_runtime_showcase.py
"""

import asyncio

from smplkit import AsyncSmplClient


async def main() -> None:

    # create the client (use SmplClient for synchronous use)
    async with AsyncSmplClient(
        environment="production", service="showcase-billing"
    ) as client:
        try:
            # declare a root config and an inheriting child via direct
            # object reference — no string id required for the parent link
            common = await client.config.get_or_create(
                "showcase-common",
                description="Shared defaults for showcase services.",
            )
            billing = await client.config.get_or_create(
                "showcase-billing",
                parent=common,
                description="Plan-limit configuration discovered from code.",
            )

            # typed getters register each item once and return the
            # current resolved value (or the in-code default when the
            # item is not yet set on the server)
            app_name = common.get_string("app.name", default="Acme SaaS")
            support_email = common.get_string("support.email", default="support@acme.dev")
            max_seats = billing.get_int(
                "plan.max_seats", default=5, description="Maximum seats per organization."
            )
            trial_days = billing.get_int("plan.trial_days", default=14)
            tier = billing.get_string("plan.tier", default="free")

            print(f"app.name = {app_name}")
            print(f"support.email = {support_email}")
            print(f"plan.max_seats = {max_seats}")
            print(f"plan.trial_days = {trial_days}")
            print(f"plan.tier = {tier}")

            # push discoveries to smplkit so admin overrides land against
            # the right keys
            await client.manage.config.flush()

            # listen for admin overrides delivered over the WebSocket
            changes: list = []

            @billing.on_change("plan.max_seats")
            def on_max_seats(event):
                changes.append(event)
                print(
                    f"    [CHANGE] {event.config_id}.{event.item_key}: "
                    f"{event.old_value!r} -> {event.new_value!r}"
                )

            # simulate someone overriding a value in the console (the
            # management API and the console UI go through the same
            # PUT endpoint)
            mgmt = await client.manage.config.get("showcase-billing")
            mgmt.set_number("plan.max_seats", 25, environment="production")
            await mgmt.save()

            # wait for the WebSocket push to deliver the change
            deadline = asyncio.get_event_loop().time() + 10.0
            while not changes and asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(0.1)

            # same typed getter, new value
            updated_seats = billing.get_int("plan.max_seats", default=5)
            print(f"plan.max_seats after override = {updated_seats}")
            assert updated_seats == 25, f"Expected 25, got {updated_seats}"
            assert len(changes) >= 1, "Expected at least one change event"
        finally:
            # delete child before parent (parents cannot be deleted while
            # children reference them)
            for cid in ("showcase-billing", "showcase-common"):
                try:
                    await client.manage.config.delete(cid)
                except Exception:
                    pass
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
