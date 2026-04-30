"""
Smpl Flags SDK Showcase — Runtime Evaluation
==============================================

Demonstrates the smplkit Python SDK's runtime evaluation for Smpl Flags.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The smplkit Flags service running and reachable
    - At least two environments configured (e.g., ``staging``, ``production``)

Usage::

    python examples/flags_runtime_showcase.py
"""

import asyncio

from smplkit import AsyncSmplClient, Context, Op, Rule

# Demo scaffolding — creates flags so this showcase can run standalone.
# In a real app, flags are created via the Console UI.
from flags_runtime_setup import setup_demo_flags, teardown_demo_flags

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


# ---------------------------------------------------------------------------
# Simulated request context
# ---------------------------------------------------------------------------
# In a real application, these would come from your web framework's
# request object (Flask, Django, FastAPI, etc.). For this showcase,
# we simulate them with mutable globals that we swap mid-script to
# demonstrate how the context provider drives flag evaluation.
# ---------------------------------------------------------------------------

_current_user = {
    "id": "user-001",
    "first_name": "Alice",
    "plan": "enterprise",
    "beta_tester": True,
}

_current_account = {
    "id": "acme-corp",
    "industry": "technology",
    "region": "us",
    "employee_count": 500,
}


def set_simulated_context(*, user: dict | None = None, account: dict | None = None):
    """Swap the simulated request context for subsequent flag evaluations."""
    global _current_user, _current_account
    if user is not None:
        _current_user = user
    if account is not None:
        _current_account = account


async def main() -> None:

    async with AsyncSmplClient(environment="staging", service="showcase-service") as client:
        step("AsyncSmplClient initialized")

        demo_keys = await setup_demo_flags(client.manage)

        # ==================================================================
        # 1. FLAG DECLARATIONS
        # ==================================================================
        #
        # Declare typed flags.  Specify the flag ID and default.  Flags do NOT
        # need to exist to begin using them.  If the flag does not exist, or
        # smplkit is unreachable or misconfigured, the code-based default will
        # be used.
        # ==================================================================

        section("1. Declare Typed Flag Handles")

        checkout_v2 = client.flags.booleanFlag("checkout-v2", default=False)
        banner_color = client.flags.stringFlag("banner-color", default="red")
        max_retries = client.flags.numberFlag("max-retries", default=3)

        # This flag doesn't exist on the server — code default will be used.
        nonexistent = client.flags.booleanFlag("feature-that-doesnt-exist", default=False)

        step(f"checkout_v2:    id={checkout_v2.id}, code_default={checkout_v2.default}")
        step(f"banner_color:   id={banner_color.id}, code_default={banner_color.default}")
        step(f"max_retries:    id={max_retries.id}, code_default={max_retries.default}")
        step(f"nonexistent:    id={nonexistent.id}, code_default={nonexistent.default}")

        # ==================================================================
        # 2. CONTEXT PROVIDER
        # ==================================================================
        #
        # The context provider is a function called on every flag.get().
        # It returns a list of Context objects, each describing a typed
        # entity in the evaluation context.
        # ==================================================================

        section("2. Register Context Provider")

        @client.flags.context_provider
        def resolve_context():
            return [
                Context(
                    "user",
                    _current_user["id"],
                    first_name=_current_user["first_name"],
                    plan=_current_user["plan"],
                    beta_tester=_current_user["beta_tester"],
                ),
                Context(
                    "account",
                    _current_account["id"],
                    industry=_current_account["industry"],
                    region=_current_account["region"],
                    employee_count=_current_account["employee_count"],
                ),
            ]

        step("Context provider registered")

        # ==================================================================
        # 3. EVALUATE FLAGS
        # ==================================================================
        #
        # Call .get() on a flag handle to read its current value for the
        # configured environment and context.
        # ==================================================================

        # ------------------------------------------------------------------
        # 3a. Evaluate with current context (Alice, enterprise, US, tech, 500)
        # ------------------------------------------------------------------
        section("3a. Evaluate Flags (Alice — enterprise, US, tech company)")

        checkout_result = checkout_v2.get()
        step(f"checkout-v2 = {checkout_result}")
        assert checkout_result is True, f"Expected True, got {checkout_result}"
        assert isinstance(checkout_result, bool), "Expected bool return type"
        # Matches: enterprise + US region

        banner_result = banner_color.get()
        step(f"banner-color = {banner_result}")
        assert banner_result == "blue", f"Expected 'blue', got {banner_result}"
        assert isinstance(banner_result, str), "Expected str return type"
        # Matches: enterprise plan (first rule)

        retries_result = max_retries.get()
        step(f"max-retries = {retries_result}")
        assert retries_result == 5, f"Expected 5, got {retries_result}"
        # Matches: employee_count 500 > 100

        nonexistent_result = nonexistent.get()
        step(f"feature-that-doesnt-exist = {nonexistent_result}")
        assert nonexistent_result is False
        # Flag not on server — code-level default used

        step("All assertions passed ✓")

        # ------------------------------------------------------------------
        # 3b. Switch context — simulate a different user/request
        # ------------------------------------------------------------------
        section("3b. Evaluate Flags (Bob — free, EU, retail, 10 employees)")

        set_simulated_context(
            user={
                "id": "user-002",
                "first_name": "Bob",
                "plan": "free",
                "beta_tester": False,
            },
            account={
                "id": "small-biz",
                "industry": "retail",
                "region": "eu",
                "employee_count": 10,
            },
        )

        checkout_result_2 = checkout_v2.get()
        step(f"checkout-v2 = {checkout_result_2}")
        assert checkout_result_2 is False
        # No rules match: not enterprise+US, not beta tester

        banner_result_2 = banner_color.get()
        step(f"banner-color = {banner_result_2}")
        assert banner_result_2 == "red"
        # No rules match; flag default = red

        retries_result_2 = max_retries.get()
        step(f"max-retries = {retries_result_2}")
        assert retries_result_2 == 3
        # No rules match: 10 employees not > 100; flag default = 3

        step("Context-dependent evaluation correct ✓")

        # Restore Alice for subsequent sections.
        set_simulated_context(
            user={"id": "user-001", "first_name": "Alice", "plan": "enterprise", "beta_tester": True},
            account={"id": "acme-corp", "industry": "technology", "region": "us", "employee_count": 500},
        )

        # ------------------------------------------------------------------
        # 3c. Explicit context override — bypass the provider
        # ------------------------------------------------------------------
        section("3c. Explicit Context Override")

        explicit_result = checkout_v2.get(
            context=[
                Context("user", "test-user", plan="free", beta_tester=False),
                Context("account", "test-account", region="jp"),
            ]
        )
        step(f"checkout-v2 (free, JP) = {explicit_result}")
        assert explicit_result is False

        explicit_result_2 = checkout_v2.get(
            context=[
                Context("user", "test-user", plan="enterprise", beta_tester=False),
                Context("account", "test-account", region="us"),
            ]
        )
        step(f"checkout-v2 (enterprise, US) = {explicit_result_2}")
        assert explicit_result_2 is True

        step("Explicit context override works ✓")

        # ==================================================================
        # 4. REAL-TIME UPDATES
        # ==================================================================
        #
        # Flag definitions stay current automatically.  Register a listener
        # to react to changes — globally, or scoped to a specific flag id.
        # ==================================================================

        section("4. Real-Time Updates")

        # ------------------------------------------------------------------
        # 4a. Register change listeners
        # ------------------------------------------------------------------

        # Global listener — fires when ANY flag definition changes.
        all_changes: list[dict] = []

        @client.flags.on_change
        def on_any_change(event):
            all_changes.append({"id": event.id, "source": event.source})
            print(f"    [GLOBAL] Flag '{event.id}' updated via {event.source}")

        step("Global change listener registered (fires for any flag)")

        # Scoped listener — fires only when a specific flag changes.
        banner_changes: list = []

        @client.flags.on_change("banner-color")
        def on_banner_change(event):
            banner_changes.append(event)
            print("    [BANNER] banner-color definition changed")

        step("Scoped listener registered for banner-color")

        checkout_changes: list = []

        @client.flags.on_change("checkout-v2")
        def on_checkout_change(event):
            checkout_changes.append(event)
            print("    [CHECKOUT] checkout-v2 definition changed")

        step("Scoped listener registered for checkout-v2")

        # ------------------------------------------------------------------
        # 4b. Simulate a change
        # ------------------------------------------------------------------
        step("Adding a rule to banner-color staging...")

        current_banner = await client.manage.flags.get("banner-color")
        current_banner.addRule(
            Rule("Red for small companies")
            .environment("staging")
            .when("account.employee_count", Op.LT, 50)
            .serve("red")
            .build()
        )
        await current_banner.save()

        # Give the WebSocket a moment to deliver the update.
        await asyncio.sleep(2)

        step(f"Global changes received: {len(all_changes)}")
        step(f"Banner-specific changes: {len(banner_changes)}")
        step(f"Checkout-specific changes: {len(checkout_changes)}")
        # Expected: global=1, banner=1, checkout=0 (only banner was changed)

        # ==================================================================
        # 5. SYNC CLIENT DEMO
        # ==================================================================
        section("5. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplClient, Context
        #
        #     with SmplClient(environment="production", service="my-service") as client:
        #
        #         @client.flags.context_provider
        #         def resolve_context():
        #             return [Context("user", request.user.id, plan=request.user.plan)]
        #
        #         checkout = client.flags.booleanFlag("checkout-v2", default=False)
        #         if checkout.get():
        #             render_new_checkout()

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 6. CLEANUP
        # ==================================================================
        section("6. Cleanup")

        await teardown_demo_flags(client.manage, demo_keys)

        section("ALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
