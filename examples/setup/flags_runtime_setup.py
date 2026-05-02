"""Setup / cleanup helpers for ``flags_runtime_showcase.py``."""

from __future__ import annotations

from smplkit import (
    AsyncSmplManagementClient,
    FlagValue,
    Op,
    Rule,
    NotFoundError,
)

_DEMO_ENVIRONMENTS = ["staging", "production"]
_DEMO_FLAG_IDS = ["checkout-v2", "banner-color", "max-retries"]


async def setup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
    existing = {env.id for env in await manage.environments.list()}
    for env_id in _DEMO_ENVIRONMENTS:
        if env_id not in existing:
            await manage.environments.new(env_id, name=env_id.title()).save()
    await cleanup_runtime_showcase(manage)

    checkout = manage.flags.new_boolean_flag(
        "checkout-v2",
        default=False,
        description="Controls rollout of the new checkout experience.",
    )
    checkout.enable_rules(environment="staging")
    checkout.add_rule(
        Rule("Enable for enterprise users in US region", environment="staging")
        .when("user.plan", Op.EQ, "enterprise")
        .when("account.region", Op.EQ, "us")
        .serve(True)
    )
    checkout.add_rule(
        Rule("Enable for beta testers", environment="staging")
        .when("user.beta_tester", Op.EQ, True)
        .serve(True)
    )
    checkout.disable_rules(environment="production")
    checkout.set_default(False, environment="production")
    await checkout.save()

    banner = manage.flags.new_string_flag(
        "banner-color",
        default="red",
        name="Banner Color",
        description="Controls the banner color shown to users.",
        values=[
            FlagValue(name="Red", value="red"),
            FlagValue(name="Green", value="green"),
            FlagValue(name="Blue", value="blue"),
        ],
    )
    banner.enable_rules(environment="staging")
    banner.add_rule(
        Rule("Blue for enterprise users", environment="staging")
        .when("user.plan", Op.EQ, "enterprise")
        .serve("blue")
    )
    banner.add_rule(
        Rule("Green for technology companies", environment="staging")
        .when("account.industry", Op.EQ, "technology")
        .serve("green")
    )
    banner.enable_rules(environment="production")
    banner.set_default("blue", environment="production")
    await banner.save()

    retries = manage.flags.new_number_flag(
        "max-retries",
        default=3,
        description="Maximum number of API retries before failing.",
    )
    retries.enable_rules(environment="staging")
    retries.add_rule(
        Rule("High retries for large accounts", environment="staging")
        .when("account.employee_count", Op.GT, 100)
        .serve(5)
    )
    retries.enable_rules(environment="production")
    await retries.save()


async def cleanup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
    for flag_id in _DEMO_FLAG_IDS:
        try:
            await manage.flags.delete(flag_id)
        except NotFoundError:
            pass
