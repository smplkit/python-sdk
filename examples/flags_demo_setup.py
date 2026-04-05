"""Demo setup helper for the flags runtime showcase.

Creates and configures demo flags so the runtime showcase can run
standalone.  Imported by ``flags_runtime_showcase.py``.
"""

from __future__ import annotations

from smplkit import AsyncSmplClient, FlagType, Rule


async def setup_demo_flags(client: AsyncSmplClient) -> list:
    """Create and configure three demo flags for the runtime showcase.

    Returns a list of [checkout_flag, banner_flag, retry_flag].
    """
    # Clean up leftover flags from previous runs.
    demo_keys = {"checkout-v2", "banner-color", "max-retries"}
    try:
        existing = await client.flags.list()
        for flag in existing:
            if flag.key in demo_keys:
                await client.flags.delete(flag.id)
    except Exception:
        pass

    # 1. checkout-v2 — boolean
    checkout_flag = await client.flags.create(
        "checkout-v2",
        name="Checkout V2",
        type=FlagType.BOOLEAN,
        default=False,
        description="Controls rollout of the new checkout experience.",
    )
    await checkout_flag.update(
        environments={
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
            "production": {
                "enabled": False,
                "default": False,
                "rules": [],
            },
        },
    )

    # 2. banner-color — string
    banner_flag = await client.flags.create(
        "banner-color",
        name="Banner Color",
        type=FlagType.STRING,
        default="red",
        description="Controls the banner color shown to users.",
        values=[
            {"name": "Red", "value": "red"},
            {"name": "Green", "value": "green"},
            {"name": "Blue", "value": "blue"},
        ],
    )
    await banner_flag.update(
        environments={
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
            "production": {
                "enabled": True,
                "default": "blue",
                "rules": [],
            },
        },
    )

    # 3. max-retries — numeric
    retry_flag = await client.flags.create(
        "max-retries",
        name="Max Retries",
        type=FlagType.NUMERIC,
        default=3,
        description="Maximum number of API retries before failing.",
        values=[
            {"name": "Low (1)", "value": 1},
            {"name": "Standard (3)", "value": 3},
            {"name": "High (5)", "value": 5},
            {"name": "Aggressive (10)", "value": 10},
        ],
    )
    await retry_flag.update(
        environments={
            "staging": {
                "enabled": True,
                "rules": [
                    Rule("High retries for large accounts")
                        .when("account.employee_count", ">", 100)
                        .serve(5)
                        .build(),
                ],
            },
            "production": {
                "enabled": True,
                "rules": [],
            },
        },
    )

    return [checkout_flag, banner_flag, retry_flag]


async def teardown_demo_flags(client: AsyncSmplClient, flags: list) -> None:
    """Delete the demo flags created by setup_demo_flags."""
    for flag in flags:
        try:
            await client.flags.delete(flag.id)
        except Exception:
            pass

    # Clean up any context types that were auto-created.
    try:
        context_types = await client.flags.list_context_types()
        for ct in context_types:
            try:
                await client.flags.delete_context_type(ct.id)
            except Exception:
                pass
    except Exception:
        pass
