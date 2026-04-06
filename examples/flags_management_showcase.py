"""
Smpl Flags SDK Showcase — Management API
==========================================

Demonstrates the smplkit Python SDK's management plane for Smpl Flags:

- Client initialization
- Creating flags (BOOLEAN, STRING, NUMERIC, JSON) via FlagType enum
- Rule builder: fluent API for constructing JSON Logic rules
- Configuring values, environments, and rules
- Convenience methods (addRule)
- Updating flag definitions
- Listing and inspecting flags
- Deleting flags
- Managing context types

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

from smplkit import AsyncSmplClient, FlagType, Rule

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

    # The SmplClient constructor resolves three required parameters:
    #
    #   api_key     — not passed here; resolved automatically from the
    #                 SMPLKIT_API_KEY environment variable or the
    #                 ~/.smplkit configuration file.
    #
    #   environment — the target environment. Can also be resolved from
    #                 SMPLKIT_ENVIRONMENT if not passed.
    #
    #   service     — identifies this SDK instance. Can also be resolved
    #                 from SMPLKIT_SERVICE if not passed.
    #
    # To pass the API key explicitly:
    #
    #   client = AsyncSmplClient(
    #       "sk_api_...",
    #       environment="staging",
    #       service="showcase-service",
    #   )
    #
    client = AsyncSmplClient(
        environment="staging",
        service="showcase-service",
    )
    step("AsyncSmplClient initialized (environment=staging, service=showcase-service)")

    # Clean up leftover flags and context types from previous runs.
    demo_flag_keys = {"checkout-v2", "banner-color", "max-retries", "ui-theme"}
    demo_ct_keys = {"user", "account"}
    try:
        existing_flags = await client.flags.list()
        for flag in existing_flags:
            if flag.key in demo_flag_keys:
                await client.flags.delete(flag.id)
    except Exception:
        pass
    try:
        existing_cts = await client.flags.list_context_types()
        for ct in existing_cts:
            if ct.key in demo_ct_keys:
                await client.flags.delete_context_type(ct.id)
    except Exception:
        pass

    # ======================================================================
    # 2. CREATE FLAGS
    # ======================================================================
    #
    # Flags are created with a key, name, type, default value, and an
    # optional values array. The key is the lone positional arg; everything
    # else is a keyword arg.
    #
    # Required: key (positional), name, type (FlagType enum), default
    # Optional: description, values
    #
    # FlagType enum: FlagType.BOOLEAN, FlagType.STRING, FlagType.NUMERIC,
    #                FlagType.JSON
    #
    # For BOOLEAN flags, the values array is auto-generated if not
    # provided: [{"name": "True", "value": true}, {"name": "False", "value": false}].
    #
    # For STRING, NUMERIC, and JSON flags, the values array defines the
    # closed set of legal values the flag can serve. The default must
    # reference a value in this set.
    # ======================================================================

    # ------------------------------------------------------------------
    # 2a. BOOLEAN flag
    # ------------------------------------------------------------------
    section("2a. Create a Boolean Flag")

    checkout_flag = await client.flags.create(
        "checkout-v2",
        name="Checkout V2",
        type=FlagType.BOOLEAN,
        default=False,
        description="Controls rollout of the new checkout experience.",
    )
    step(f"Created: key={checkout_flag.key}, type={checkout_flag.type}")
    step(f"  id={checkout_flag.id}")
    step(f"  values={checkout_flag.values}")
    step(f"  default={checkout_flag.default}")
    # values auto-generated: [{"name": "True", "value": true}, {"name": "False", "value": false}]

    # ------------------------------------------------------------------
    # 2b. STRING flag
    # ------------------------------------------------------------------
    section("2b. Create a String Flag")

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
    step(f"Created: key={banner_flag.key}, type={banner_flag.type}")
    step(f"  values={banner_flag.values}")

    # ------------------------------------------------------------------
    # 2c. NUMERIC flag
    # ------------------------------------------------------------------
    section("2c. Create a Numeric Flag")

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
    step(f"Created: key={retry_flag.key}, type={retry_flag.type}")

    # ------------------------------------------------------------------
    # 2d. JSON flag
    # ------------------------------------------------------------------
    section("2d. Create a JSON Flag")

    theme_flag = await client.flags.create(
        "ui-theme",
        name="UI Theme",
        type=FlagType.JSON,
        default={"mode": "light", "accent": "#0066cc"},
        description="Controls the UI theme configuration.",
        values=[
            {"name": "Light", "value": {"mode": "light", "accent": "#0066cc"}},
            {"name": "Dark", "value": {"mode": "dark", "accent": "#66ccff"}},
            {"name": "High Contrast", "value": {"mode": "dark", "accent": "#ffffff"}},
        ],
    )
    step(f"Created: key={theme_flag.key}, type={theme_flag.type}")

    # ======================================================================
    # 3. CONFIGURE ENVIRONMENTS AND RULES
    # ======================================================================
    #
    # Each flag can be independently configured per environment. An
    # environment entry includes:
    #   - enabled (bool): whether rules are evaluated
    #   - default (optional): environment-level override of the flag default
    #   - rules (array): ordered list of rules (first match wins)
    #
    # Rules can be built using the Rule builder (recommended) or as raw
    # JSON Logic dicts. The Rule builder provides a fluent API:
    #
    #   Rule("description")
    #       .when("user.plan", "==", "enterprise")
    #       .serve(True)
    #       .build()
    #
    # Multiple .when() calls are AND'd. .serve() sets the value.
    # .build() finalizes the rule as a dict ready for the API.
    # .environment() is optional — used with addRule (see section 5).
    #
    # Supported operators: ==, !=, >, <, >=, <=, in, contains
    # ======================================================================

    # ------------------------------------------------------------------
    # 3a. Configure checkout-v2 environments
    # ------------------------------------------------------------------
    section("3a. Configure checkout-v2 Environments")

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
                    Rule("Enable for beta testers").when("user.beta_tester", "==", True).serve(True).build(),
                ],
            },
            "production": {
                "enabled": False,
                "default": False,
                "rules": [],
            },
        },
    )
    step("staging: enabled with 2 targeting rules")
    step("production: disabled, default=false")

    # ------------------------------------------------------------------
    # 3b. Configure banner-color environments
    # ------------------------------------------------------------------
    section("3b. Configure banner-color Environments")

    await banner_flag.update(
        environments={
            "staging": {
                "enabled": True,
                "rules": [
                    Rule("Blue for enterprise users").when("user.plan", "==", "enterprise").serve("blue").build(),
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
    step("staging: enabled with 2 rules")
    step("production: enabled, no rules, default override = blue")

    # ------------------------------------------------------------------
    # 3c. Configure max-retries environments
    # ------------------------------------------------------------------
    section("3c. Configure max-retries Environments")

    await retry_flag.update(
        environments={
            "staging": {
                "enabled": True,
                "rules": [
                    Rule("High retries for large accounts").when("account.employee_count", ">", 100).serve(5).build(),
                ],
            },
            "production": {
                "enabled": True,
                "rules": [],
            },
        },
    )
    step("staging: enabled with 1 rule")
    step("production: enabled, no rules")

    # ======================================================================
    # 4. INSPECT AND LIST FLAGS
    # ======================================================================

    section("4. List and Inspect Flags")

    # List all flags.
    flags = await client.flags.list()
    step(f"Total flags: {len(flags)}")
    for f in flags:
        env_keys = list(f.environments.keys()) if f.environments else []
        step(f"  {f.key} ({f.type}) — default={f.default}, environments={env_keys}")

    # Fetch a single flag by ID.
    fetched = await client.flags.get(checkout_flag.id)
    step(f"\nFetched by ID: {fetched.key}")
    step(f"  staging rules: {len(fetched.environments.get('staging', {}).get('rules', []))}")
    step(f"  production enabled: {fetched.environments.get('production', {}).get('enabled')}")

    # ======================================================================
    # 5. UPDATE A FLAG
    # ======================================================================

    section("5. Update a Flag")

    # Add a new value to banner-color.
    step("Adding 'Purple' to banner-color values...")
    current_values = banner_flag.values
    current_values.append({"name": "Purple", "value": "purple"})
    await banner_flag.update(values=current_values)
    step(f"Updated values: {[v['name'] for v in banner_flag.values]}")

    # Change the flag-level default.
    step("Changing banner-color default to 'blue'...")
    await banner_flag.update(default="blue")
    step(f"Updated default: {banner_flag.default}")

    # Add a rule to an existing environment — the hard way (raw JSON Logic).
    # You have to fetch current state, build the dict, append, and send
    # the whole environments object.
    step("Adding a rule to banner-color production (raw JSON Logic)...")
    current_envs = banner_flag.environments
    prod = current_envs.get("production", {"enabled": True, "rules": []})
    prod_rules = prod.get("rules", [])
    prod_rules.append(
        {
            "description": "Purple for enterprise users",
            "logic": {"==": [{"var": "user.plan"}, "enterprise"]},
            "value": "purple",
        }
    )
    await banner_flag.update(
        environments={
            **current_envs,
            "production": {**prod, "rules": prod_rules},
        },
    )
    step(f"Production now has {len(prod_rules)} rule(s)")

    # Add a rule — the easy way. addRule takes a single built Rule.
    # The Rule's .environment() tells addRule where to insert it.
    step("Adding another rule to banner-color production (addRule + Rule)...")
    await banner_flag.addRule(
        Rule("Green for retail companies")
        .environment("production")
        .when("account.industry", "==", "retail")
        .serve("green")
        .build()
    )
    step("Rule added — no manual environment juggling, no raw JSON Logic")

    # Verify both rules are there.
    refreshed = await client.flags.get(banner_flag.id)
    prod_rules = refreshed.environments.get("production", {}).get("rules", [])
    step(f"Production rules after both additions: {len(prod_rules)}")
    for i, rule in enumerate(prod_rules):
        step(f"  [{i}] {rule.get('description', 'no description')}")

    # ======================================================================
    # 6. CONTEXT TYPE MANAGEMENT
    # ======================================================================
    #
    # Context types define the shape of data that rules can target. They
    # are typically auto-created by the SDK during runtime context
    # registration, but can also be managed explicitly via the API —
    # useful for setting up the Console rule builder before any SDK is
    # deployed.
    # ======================================================================

    section("6. Context Type Management")

    # Create context types that the Console rule builder will use.
    user_ct = await client.flags.create_context_type(
        "user",
        name="User",
    )
    step(f"Created context type: key={user_ct.key}, name={user_ct.name}")

    # Add known attributes.
    await client.flags.update_context_type(
        user_ct.id,
        key=user_ct.key,
        name=user_ct.name,
        attributes={
            "first_name": {},
            "plan": {},
            "beta_tester": {},
        },
    )
    step(f"Added attributes: {list(user_ct.attributes.keys())}")

    account_ct = await client.flags.create_context_type(
        "account",
        name="Account",
    )
    await client.flags.update_context_type(
        account_ct.id,
        key=account_ct.key,
        name=account_ct.name,
        attributes={
            "industry": {},
            "region": {},
            "employee_count": {},
        },
    )
    step(f"Created context type: key={account_ct.key}")

    # List context types.
    context_types = await client.flags.list_context_types()
    for ct in context_types:
        attrs = list(ct.attributes.keys()) if ct.attributes else []
        step(f"  {ct.key}: attributes={attrs}")

    # ======================================================================
    # 7. CLEANUP
    # ======================================================================
    section("7. Cleanup")

    # Delete flags.
    for flag in [checkout_flag, banner_flag, retry_flag, theme_flag]:
        await client.flags.delete(flag.id)
        step(f"Deleted flag: {flag.key}")

    # Delete context types.
    for ct in [user_ct, account_ct]:
        await client.flags.delete_context_type(ct.id)
        step(f"Deleted context type: {ct.key}")

    # Close the client.
    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Flags Management showcase completed successfully.")
    print("  All flags and context types have been cleaned up.\n")


if __name__ == "__main__":
    asyncio.run(main())
