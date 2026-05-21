"""
Demonstrates the smplkit runtime SDK for Smpl Config.

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

from setup.config_runtime_setup import (
    cleanup_runtime_showcase,
    setup_runtime_showcase,
    simulate_admin_override,
)


async def main() -> None:

    # create the client (use SmplClient for synchronous use)
    async with AsyncSmplClient(
        environment="production", service="showcase-billing"
    ) as client:
        await setup_runtime_showcase(client.manage)

        # declare a common/shared configuration
        common = await client.config.get_or_create(
            "showcase-common",
            description="Shared defaults for showcase services.",
        )

        # declare a configuration that inherits from some parent
        billing = await client.config.get_or_create(
            "showcase-billing",
            parent=common,
            description="Plan-limit configuration discovered from code.",
        )

        # get a configured value
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

        # listen for changes
        changes: list = []

        @billing.on_change("plan.max_seats")
        def on_max_seats(event):
            changes.append(event)
            print(
                f"    [CHANGE] {event.config_id}.{event.item_key}: "
                f"{event.old_value!r} -> {event.new_value!r}"
            )

        # simulate someone overriding a value in the console
        await simulate_admin_override(client.manage)

        # wait for the WebSocket push to deliver the change
        await asyncio.sleep(0.4)

        # get the latest value
        updated_seats = billing.get_int("plan.max_seats", default=5)
        print(f"plan.max_seats after override = {updated_seats}")
        assert updated_seats == 25, f"Expected 25, got {updated_seats}"
        assert len(changes) >= 1, "Expected at least one change event"

        await cleanup_runtime_showcase(client.manage)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
