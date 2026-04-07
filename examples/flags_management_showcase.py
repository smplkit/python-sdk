"""
Smpl Flags SDK Showcase — Management API
==========================================

Demonstrates the smplkit Python SDK's management plane for Smpl Flags:

- Client initialization (no connect() needed for management)
- Typed flag creation via factory methods: newBooleanFlag, newStringFlag,
  newNumberFlag, newJsonFlag
- Active record pattern: local mutations + save() to persist
- Rule builder: fluent API for constructing JSON Logic rules
- addRule() as local mutation, save() to persist
- Environment convenience methods: setEnvironmentEnabled, setEnvironmentDefault
- Listing and inspecting flags via get(key) and list()
- Deleting flags by key

Most customers will create and configure flags via the Console UI.
This showcase demonstrates the programmatic equivalent — useful for
infrastructure-as-code, CI/CD pipelines, setup scripts, and automated
testing.

For the runtime evaluation experience (declaring flags in code,
evaluating them, context providers, caching, live updates), see
``flags_runtime_showcase.py``.

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

from smplkit import AsyncSmplClient, Rule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def section(title: str) -> None:
    """Print a section header for readability."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def step(description: str) -> None:
    """Print a step within a section."""
    print(f"  → {description}")


async def main() -> None:

    # ======================================================================
    # 1. SDK INITIALIZATION
    # ======================================================================
    section("1. SDK Initialization")

    # Management operations do not require connect() or start() — they
    # are stateless HTTP calls. The constructor resolves environment,
    # service, and API key, then registers the service with the server.
    async with AsyncSmplClient(environment="staging", service="showcase-service") as client:

        step("AsyncSmplClient initialized (environment=staging, service=showcase-service)")

        # Clean up leftover flags from previous runs.
        demo_flag_keys = {"checkout-v2", "banner-color", "max-retries", "ui-theme"}
        try:
            existing_flags = await client.flags.list()
            for flag in existing_flags:
                if flag.key in demo_flag_keys:
                    await client.flags.delete(flag.key)
        except Exception:
            pass

        # ==================================================================
        # 2. CREATE FLAGS — Typed Factory Methods
        # ==================================================================
        #
        # Flags are created via typed factory methods on the FlagsClient:
        #
        #   newBooleanFlag(key, *, default, name=None, description=None)
        #   newStringFlag(key, *, default, name=None, description=None, values=None)
        #   newNumberFlag(key, *, default, name=None, description=None, values=None)
        #   newJsonFlag(key, *, default, name=None, description=None, values=None)
        #
        # These return an unsaved Flag instance (id=None). Nothing is sent
        # to the server until .save() is called. The flag type is implicit
        # in the factory method name — no FlagType enum needed.
        #
        # When name is omitted, the SDK generates a display name from the
        # key (e.g., "checkout-v2" → "Checkout V2").
        # ==================================================================

        # ------------------------------------------------------------------
        # 2a. BOOLEAN flag
        # ------------------------------------------------------------------
        section("2a. Create a Boolean Flag")

        checkout_flag = client.flags.newBooleanFlag(
            "checkout-v2",
            default=False,
            description="Controls rollout of the new checkout experience.",
        )
        step(f"Created locally: key={checkout_flag.key}, type={checkout_flag.type}")
        step(f"  id={checkout_flag.id}  (None — not yet saved)")
        step(f"  default={checkout_flag.default}")

        await checkout_flag.save()
        step(f"  Saved → id={checkout_flag.id}")

        # ------------------------------------------------------------------
        # 2b. STRING flag
        # ------------------------------------------------------------------
        section("2b. Create a String Flag")

        banner_flag = client.flags.newStringFlag(
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
        step(f"Created and saved: key={banner_flag.key}, type={banner_flag.type}")
        step(f"  values={banner_flag.values}")

        # ------------------------------------------------------------------
        # 2c. NUMERIC flag
        # ------------------------------------------------------------------
        section("2c. Create a Numeric Flag")

        retry_flag = client.flags.newNumberFlag(
            "max-retries",
            default=3,
            description="Maximum number of API retries before failing.",
            values=[
                {"name": "Low (1)", "value": 1},
                {"name": "Standard (3)", "value": 3},
                {"name": "High (5)", "value": 5},
                {"name": "Aggressive (10)", "value": 10},
            ],
        )
        await retry_flag.save()
        step(f"Created and saved: key={retry_flag.key}, type={retry_flag.type}")

        # ------------------------------------------------------------------
        # 2d. JSON flag
        # ------------------------------------------------------------------
        section("2d. Create a JSON Flag")

        theme_flag = client.flags.newJsonFlag(
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
        step(f"Created and saved: key={theme_flag.key}, type={theme_flag.type}")

        # ==================================================================
        # 3. CONFIGURE ENVIRONMENTS AND RULES
        # ==================================================================
        #
        # Each flag can be independently configured per environment. Use
        # convenience methods for common operations, or manipulate the
        # environments dict directly for full control.
        #
        # All mutations are LOCAL until save() is called. This lets you
        # preview the full state before persisting.
        #
        # Rules can be built using the Rule builder (recommended) or as
        # raw JSON Logic dicts.
        #
        #   Rule("description")
        #       .environment("staging")       # which env to target
        #       .when("user.plan", "==", "enterprise")
        #       .serve(True)
        #       .build()
        #
        # Multiple .when() calls are AND'd. Supported operators:
        #   ==, !=, >, <, >=, <=, in, contains
        # ==================================================================

        # ------------------------------------------------------------------
        # 3a. Configure checkout-v2 environments
        # ------------------------------------------------------------------
        section("3a. Configure checkout-v2 Environments")

        # Convenience methods — local mutations, no API call
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

        checkout_flag.setEnvironmentEnabled("production", False)
        checkout_flag.setEnvironmentDefault("production", False)

        # All mutations are local — now persist
        await checkout_flag.save()
        step("staging: enabled with 2 targeting rules")
        step("production: disabled, default=false")
        step("All changes persisted via single save()")

        # ------------------------------------------------------------------
        # 3b. Configure banner-color environments
        # ------------------------------------------------------------------
        section("3b. Configure banner-color Environments")

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

        # List all flags — always an HTTP request.
        flags = await client.flags.list()
        step(f"Total flags: {len(flags)}")
        for f in flags:
            env_keys = list(f.environments.keys()) if f.environments else []
            step(f"  {f.key} ({f.type}) — default={f.default}, environments={env_keys}")

        # Fetch a single flag by key — always an HTTP request.
        fetched = await client.flags.get("checkout-v2")
        step(f"\nFetched by key: {fetched.key}")
        step(f"  staging rules: {len(fetched.environments.get('staging', {}).get('rules', []))}")
        step(f"  production enabled: {fetched.environments.get('production', {}).get('enabled')}")

        # ==================================================================
        # 5. UPDATE A FLAG — Active Record Pattern
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
        refreshed = await client.flags.get("banner-color")
        prod_rules = refreshed.environments.get("production", {}).get("rules", [])
        step(f"Production rules after save: {len(prod_rules)}")
        for i, rule in enumerate(prod_rules):
            step(f"  [{i}] {rule.get('description', 'no description')}")

        # ==================================================================
        # 6. CLEAR RULES AND ENVIRONMENT CONVENIENCE METHODS
        # ==================================================================

        section("6. Environment Convenience Methods")

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
        #     from smplkit import SmplClient, Rule
        #
        #     with SmplClient(environment="staging", service="my-service") as client:
        #
        #         # Create a flag — local, then persist
        #         flag = client.flags.newBooleanFlag("my-flag", default=False)
        #         flag.save()
        #
        #         # Fetch, mutate, save
        #         flag = client.flags.get("my-flag")
        #         flag.setEnvironmentEnabled("staging", True)
        #         flag.addRule(
        #             Rule("...").environment("staging").when(...).serve(True).build()
        #         )
        #         flag.save()
        #
        #         # List and delete
        #         flags = client.flags.list()
        #         client.flags.delete("my-flag")

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 8. CLEANUP
        # ==================================================================
        section("8. Cleanup")

        for key in ["checkout-v2", "banner-color", "max-retries", "ui-theme"]:
            await client.flags.delete(key)
            step(f"Deleted flag: {key}")

        # ==================================================================
        # DONE
        # ==================================================================
        section("ALL DONE")
        print("  The Flags Management showcase completed successfully.")
        print("  All flags have been cleaned up.\n")


if __name__ == "__main__":
    asyncio.run(main())
