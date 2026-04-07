"""
Demo flag setup for the Flags Runtime Showcase.

Creates and configures demo flags so the runtime showcase can run standalone.
In a real application, flags are created via the Console UI — this file
exists only as test scaffolding.

See flags_management_showcase.py for the full management API walkthrough.
"""

from __future__ import annotations

from smplkit import AsyncSmplClient, Rule


async def setup_demo_flags(client: AsyncSmplClient) -> list[str]:
    """Create and configure three demo flags for the runtime showcase.

    Returns a list of flag keys for cleanup.
    """
    demo_keys = ["checkout-v2", "banner-color", "max-retries"]

    # Clean up leftover flags from previous runs.
    try:
        existing = await client.flags.list()
        for flag in existing:
            if flag.key in demo_keys:
                await client.flags.delete(flag.key)
    except Exception:
        pass

    # 1. checkout-v2 — boolean
    checkout = client.flags.newBooleanFlag("checkout-v2", default=False,
        description="Controls rollout of the new checkout experience.")
    checkout.setEnvironmentEnabled("staging", True)
    checkout.addRule(
        Rule("Enable for enterprise users in US region")
        .environment("staging")
        .when("user.plan", "==", "enterprise")
        .when("account.region", "==", "us")
        .serve(True)
        .build()
    )
    checkout.addRule(
        Rule("Enable for beta testers")
        .environment("staging")
        .when("user.beta_tester", "==", True)
        .serve(True)
        .build()
    )
    checkout.setEnvironmentEnabled("production", False)
    checkout.setEnvironmentDefault("production", False)
    await checkout.save()

    # 2. banner-color — string
    banner = client.flags.newStringFlag("banner-color", default="red",
        name="Banner Color",
        description="Controls the banner color shown to users.",
        values=[
            {"name": "Red", "value": "red"},
            {"name": "Green", "value": "green"},
            {"name": "Blue", "value": "blue"},
        ])
    banner.setEnvironmentEnabled("staging", True)
    banner.addRule(
        Rule("Blue for enterprise users")
        .environment("staging")
        .when("user.plan", "==", "enterprise")
        .serve("blue")
        .build()
    )
    banner.addRule(
        Rule("Green for technology companies")
        .environment("staging")
        .when("account.industry", "==", "technology")
        .serve("green")
        .build()
    )
    banner.setEnvironmentEnabled("production", True)
    banner.setEnvironmentDefault("production", "blue")
    await banner.save()

    # 3. max-retries — numeric
    retries = client.flags.newNumberFlag("max-retries", default=3,
        description="Maximum number of API retries before failing.",
        values=[
            {"name": "Low (1)", "value": 1},
            {"name": "Standard (3)", "value": 3},
            {"name": "High (5)", "value": 5},
            {"name": "Aggressive (10)", "value": 10},
        ])
    retries.setEnvironmentEnabled("staging", True)
    retries.addRule(
        Rule("High retries for large accounts")
        .environment("staging")
        .when("account.employee_count", ">", 100)
        .serve(5)
        .build()
    )
    retries.setEnvironmentEnabled("production", True)
    await retries.save()

    return demo_keys


async def teardown_demo_flags(client: AsyncSmplClient, keys: list[str]) -> None:
    """Delete the demo flags created by setup_demo_flags."""
    for key in keys:
        try:
            await client.flags.delete(key)
        except Exception:
            pass
