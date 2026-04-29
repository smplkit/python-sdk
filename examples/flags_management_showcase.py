"""
Smpl Flags SDK Showcase — Management API
==========================================

Demonstrates the smplkit Python SDK's management plane for Smpl Flags.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The smplkit Flags service running and reachable
    - At least two environments configured (e.g., ``staging``, ``production``)

Usage::

    python examples/flags_management_showcase.py
"""

import asyncio

from smplkit import AsyncSmplManagementClient, Rule


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}\n")


def step(description: str) -> None:
    print(f"  → {description}")


async def main() -> None:

    # create the client (use SmplManagementClient for synchronous use)
    async with AsyncSmplManagementClient() as mgmt:
        # TODO move this code into a non-descript cleanup() method without
        #  any comment here about it
        demo_flag_ids = {"checkout-v2", "banner-color", "max-retries", "ui-theme"}
        try:
            existing_flags = await mgmt.flags.list()
            for flag in existing_flags:
                if flag.id in demo_flag_ids:
                    await mgmt.flags.delete(flag.id)
        except Exception:
            pass

        # create flags
        checkout_flag = mgmt.flags.newBooleanFlag(
            "checkout-v2",
            default=False,
            description="Controls rollout of the new checkout experience.",
        )
        await checkout_flag.save()

        banner_flag = mgmt.flags.newStringFlag(
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

        retry_flag = mgmt.flags.newNumberFlag(
            "max-retries",
            default=3,
            description="Maximum number of API retries before failing.",
        )
        await retry_flag.save()

        theme_flag = mgmt.flags.newJsonFlag(
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

        # create rules for staging
        checkout_flag.setEnvironmentEnabled("staging", True)
        checkout_flag.addRule(
            Rule("Enable for enterprise users in US region")
            .environment("staging")
            .when("user.plan", "==", "enterprise")
            .when("account.region", "==", "us")
            .serve(True)
            .build()
        )
        checkout_flag.addRule(
            Rule("Enable for beta testers")
            .environment("staging")
            .when("user.beta_tester", "==", True)
            .serve(True)
            .build()
        )

        # disable rules in production; serve false to everyone
        checkout_flag.setEnvironmentEnabled("production", False)
        checkout_flag.setEnvironmentDefault("production", False)
        await checkout_flag.save()

        # create more rules
        banner_flag.setEnvironmentEnabled("staging", True)
        banner_flag.addRule(
            Rule("Blue for enterprise users")
            .environment("staging")
            .when("user.plan", "==", "enterprise")
            .serve("blue")
            .build()
        )
        banner_flag.addRule(
            Rule("Green for technology companies")
            .environment("staging")
            .when("account.industry", "==", "technology")
            .serve("green")
            .build()
        )

        # enable all rules for this flag in production; serve 'blue' if no rules match
        banner_flag.setEnvironmentEnabled("production", True)
        banner_flag.setEnvironmentDefault("production", "blue")

        await banner_flag.save()
        step("staging: enabled with 2 rules")
        step("production: enabled, no rules, default override = blue")

        # ------------------------------------------------------------------
        # 3c. Configure max-retries environments
        # ------------------------------------------------------------------
        section("3c. Configure max-retries Environments")

        retry_flag.setEnvironmentEnabled("staging", True)
        retry_flag.addRule(
            Rule("High retries for large accounts")
            .environment("staging")
            .when("account.employee_count", ">", 100)
            .serve(5)
            .build()
        )

        retry_flag.setEnvironmentEnabled("production", True)

        await retry_flag.save()
        step("staging: enabled with 1 rule")
        step("production: enabled, no rules")

        # ==================================================================
        # 4. INSPECT AND LIST FLAGS
        # ==================================================================

        section("4. List and Inspect Flags")

        # List all flags.
        flags = await mgmt.flags.list()
        step(f"Total flags: {len(flags)}")
        for f in flags:
            env_keys = list(f.environments.keys()) if f.environments else []
            step(f"  {f.id} ({f.type}) — default={f.default}, environments={env_keys}")

        # Fetch a single flag by id.
        fetched = await mgmt.flags.get("checkout-v2")
        step(f"\nFetched by id: {fetched.id}")
        step(f"  staging rules: {len(fetched.environments.get('staging', {}).get('rules', []))}")
        step(f"  production enabled: {fetched.environments.get('production', {}).get('enabled')}")

        # ==================================================================
        # 5. UPDATE A FLAG
        # ==================================================================

        section("5. Update a Flag")

        # Fetch → mutate → save. All mutations are local until save().

        # Add a new value to banner-color.
        step("Adding 'Purple' to banner-color values...")
        banner_flag.values.append({"name": "Purple", "value": "purple"})
        step(f"Values (local): {[v['name'] for v in banner_flag.values]}")

        # Change the flag-level default.
        banner_flag.default = "blue"
        step(f"Default (local): {banner_flag.default}")

        # Change description.
        banner_flag.description = "Controls the banner color — updated"
        step(f"Description (local): {banner_flag.description}")

        # Add a rule to production using addRule (local mutation).
        banner_flag.addRule(
            Rule("Purple for enterprise users")
            .environment("production")
            .when("user.plan", "==", "enterprise")
            .serve("purple")
            .build()
        )
        step("Added rule to production (local)")

        banner_flag.addRule(
            Rule("Green for retail companies")
            .environment("production")
            .when("account.industry", "==", "retail")
            .serve("green")
            .build()
        )
        step("Added another rule to production (local)")

        # Single save() persists all accumulated mutations.
        await banner_flag.save()
        step("All changes persisted via single save()")

        # Verify by re-fetching.
        refreshed = await mgmt.flags.get("banner-color")
        prod_rules = refreshed.environments.get("production", {}).get("rules", [])
        step(f"Production rules after save: {len(prod_rules)}")
        for i, rule in enumerate(prod_rules):
            step(f"  [{i}] {rule.get('description', 'no description')}")

        # ==================================================================
        # 6. CLEAR RULES
        # ==================================================================

        section("6. Clear Rules")

        # clearRules() removes all rules from an environment.
        checkout_flag.clearRules("staging")
        step("Cleared all staging rules on checkout-v2 (local)")

        # Raw dict manipulation is always available as an alternative.
        checkout_flag.environments["production"] = {"enabled": True, "default": True, "rules": []}
        step("Set production via raw dict (local)")

        await checkout_flag.save()
        step("Persisted")

        # ==================================================================
        # 7. SYNC CLIENT DEMO
        # ==================================================================
        section("7. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplManagementClient, Rule
        #
        #     with SmplManagementClient() as mgmt:
        #
        #         # Create a flag — local, then persist
        #         flag = mgmt.flags.newBooleanFlag("my-flag", default=False)
        #         flag.save()
        #
        #         # Fetch, mutate, save
        #         flag = mgmt.flags.get("my-flag")
        #         flag.setEnvironmentEnabled("staging", True)
        #         flag.addRule(
        #             Rule("...").environment("staging").when(...).serve(True).build()
        #         )
        #         flag.save()
        #
        #         # List and delete
        #         flags = mgmt.flags.list()
        #         mgmt.flags.delete("my-flag")

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 8. CLEANUP
        # ==================================================================
        section("8. Cleanup")

        for flag_id in ["checkout-v2", "banner-color", "max-retries", "ui-theme"]:
            await mgmt.flags.delete(flag_id)
            step(f"Deleted flag: {flag_id}")

        section("ALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
