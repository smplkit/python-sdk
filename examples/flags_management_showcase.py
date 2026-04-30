"""
Smpl Flags SDK Showcase — Management API
==========================================

Demonstrates the smplkit Python SDK's management plane for Smpl Flags.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/flags_management_showcase.py
"""

import asyncio

from smplkit import AsyncSmplManagementClient, Op, Rule

from flags_management_setup import cleanup_management_showcase, setup_management_showcase


async def main() -> None:

    # create the client (use SmplManagementClient for synchronous use)
    async with AsyncSmplManagementClient() as manage:
        await setup_management_showcase(manage)

        # create a boolean flag
        checkout_flag = manage.flags.newBooleanFlag(
            "checkout-v2",
            default=False,
            description="Controls rollout of the new checkout experience.",
        )
        await checkout_flag.save()
        print(f"Created flag: {checkout_flag.id}")

        # create a string flag (constrained)
        banner_flag = manage.flags.newStringFlag(
            "banner-color",
            default="red",
            name="Banner Color",
            description="Controls the banner color shown to users.",
            values=[
                {"name": "Red", "value": "red"},
                {"name": "Green", "value": "green"},
                {"name": "Blue", "value": "blue"},
            ],
        )
        await banner_flag.save()
        print(f"Created flag: {banner_flag.id}")

        # create a numeric flag (unconstrained)
        retry_flag = manage.flags.newNumberFlag(
            "max-retries",
            default=3,
            description="Maximum number of API retries before failing.",
        )
        await retry_flag.save()
        print(f"Created flag: {retry_flag.id}")

        # create a JSON flag (constrained)
        theme_flag = manage.flags.newJsonFlag(
            "ui-theme",
            default={"mode": "light", "accent": "#0066cc"},
            description="Controls the UI theme configuration.",
            values=[
                {"name": "Light", "value": {"mode": "light", "accent": "#0066cc"}},
                {"name": "Dark", "value": {"mode": "dark", "accent": "#66ccff"}},
                {"name": "High Contrast", "value": {"mode": "dark", "accent": "#ffffff"}},
            ],
        )
        await theme_flag.save()
        print(f"Created flag: {theme_flag.id}")

        # checkout_flag: serve true in staging to enterprise users in the US region
        checkout_flag.setEnvironmentEnabled("staging", True)
        checkout_flag.addRule(
            Rule("Enable for enterprise users in US region")
            .environment("staging")
            .when("user.plan", Op.EQ, "enterprise")
            .when("account.region", Op.EQ, "us")
            .serve(True)
            .build()
        )

        # checkout_flag: serve true in staging for beta testers
        checkout_flag.addRule(
            Rule("Enable for beta testers")
            .environment("staging")
            .when("user.beta_tester", Op.EQ, True)
            .serve(True)
            .build()
        )

        # checkout_flag: serve false in production
        checkout_flag.setEnvironmentEnabled("production", False)
        checkout_flag.setEnvironmentDefault("production", False)
        await checkout_flag.save()
        print(f"Updated flag: {checkout_flag.id}")

        # list flags
        flags = await manage.flags.list()
        print(f"Total flags: {len(flags)}")
        for f in flags:
            env_keys = list(f.environments.keys()) if f.environments else []
            print(f"  {f.id} ({f.type}) — default={f.default}, environments={env_keys}")

        # get a flag
        fetched = await manage.flags.get("checkout-v2")
        print(f"\nFetched by id: {fetched.id}")
        print(f"  staging rules: {len(fetched.environments.get('staging', {}).get('rules', []))}")
        print(f"  production enabled: {fetched.environments.get('production', {}).get('enabled')}")

        # update a flag
        banner_flag.values.append({"name": "Purple", "value": "purple"})
        banner_flag.default = "blue"
        banner_flag.description = "Controls the banner color — updated"
        banner_flag.addRule(
            Rule("Purple for enterprise users")
            .environment("production")
            .when("user.plan", Op.EQ, "enterprise")
            .serve("purple")
            .build()
        )
        await banner_flag.save()
        print(f"Updated flag: {banner_flag.id}'")

        # update a flag - delete all rules
        checkout_flag.clearRules("staging")

        # alternatively:
        # checkout_flag.environments["staging"] = {"enabled": True, "default": True, "rules": []}
        await checkout_flag.save()
        print(f"Updated flag: {checkout_flag.id}'")

        # cleanup
        await cleanup_management_showcase(manage)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
