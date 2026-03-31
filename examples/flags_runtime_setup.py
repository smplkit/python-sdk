"""
Demo flag setup for the Flags Runtime Showcase.

Creates and configures demo flags so the runtime showcase can run standalone.
In a real application, flags are created via the Console UI — this file
exists only as test scaffolding.

See flags_management_showcase.py for the full management API walkthrough.
"""

from smplkit import AsyncSmplClient, FlagType, Rule


async def setup_demo_flags(client: AsyncSmplClient) -> list:
    """Create demo flags. Returns list of flag objects for cleanup."""

    checkout = await client.flags.create(
        "checkout-v2",
        name="Checkout V2",
        type=FlagType.BOOLEAN,
        default=False,
    )
    await checkout.update(environments={
        "staging": {
            "enabled": True,
            "rules": [
                Rule("Enable for enterprise users in US region")
                    .when("user.plan", "==", "enterprise")
                    .when("account.region", "==", "us")
                    .serve(True)
                    .build(),
                Rule("Enable for beta testers")
                    .when("user.beta_tester", "==", True)
                    .serve(True)
                    .build(),
            ],
        },
        "production": {"enabled": False, "default": False, "rules": []},
    })

    banner = await client.flags.create(
        "banner-color",
        name="Banner Color",
        type=FlagType.STRING,
        default="red",
        values=[
            {"name": "Red", "value": "red"},
            {"name": "Green", "value": "green"},
            {"name": "Blue", "value": "blue"},
        ],
    )
    await banner.update(environments={
        "staging": {
            "enabled": True,
            "rules": [
                Rule("Blue for enterprise users")
                    .when("user.plan", "==", "enterprise")
                    .serve("blue")
                    .build(),
                Rule("Green for technology companies")
                    .when("account.industry", "==", "technology")
                    .serve("green")
                    .build(),
            ],
        },
        "production": {"enabled": True, "default": "blue", "rules": []},
    })

    retries = await client.flags.create(
        "max-retries",
        name="Max Retries",
        type=FlagType.NUMERIC,
        default=3,
        values=[
            {"name": "Low (1)", "value": 1},
            {"name": "Standard (3)", "value": 3},
            {"name": "High (5)", "value": 5},
            {"name": "Aggressive (10)", "value": 10},
        ],
    )
    await retries.update(environments={
        "staging": {
            "enabled": True,
            "rules": [
                Rule("High retries for large accounts")
                    .when("account.employee_count", ">", 100)
                    .serve(5)
                    .build(),
            ],
        },
        "production": {"enabled": True, "rules": []},
    })

    return [checkout, banner, retries]


async def teardown_demo_flags(client: AsyncSmplClient, flags: list) -> None:
    """Delete demo flags and auto-created context types."""
    for flag in flags:
        await client.flags.delete(flag.id)
    for ct in await client.flags.list_context_types():
        await client.flags.delete_context_type(ct.id)
