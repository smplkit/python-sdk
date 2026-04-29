"""
Smpl Flags SDK Showcase — Runtime Evaluation
==============================================

Demonstrates the smplkit Python SDK's runtime evaluation for Smpl Flags:

- Typed flag declarations with code-level defaults (booleanFlag, etc.)
- Context providers and typed context entities
- Explicit context registration (middleware pattern)
- Lazy initialization — first .get() fetches flags and opens WebSocket
- Evaluating flags — local JSON Logic, no network per call
- Resolution caching and cache stats
- Explicit context overrides
- Real-time updates via WebSocket and change listeners
- @client.flags.on_change decorator with optional id scoping

This is the SDK experience that 99%% of customers will use. Flags are
created and configured via the Console UI (or the management API shown
in ``flags_management_showcase.py``). This script focuses entirely on
the runtime: declaring, evaluating, and reacting to changes.

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

from smplkit import AsyncSmplClient, AsyncSmplManagementClient, Context, Rule

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

    async with (
        AsyncSmplClient(environment="staging", service="showcase-service") as client,
        AsyncSmplManagementClient() as mgmt,
    ):
        step("AsyncSmplClient initialized (environment=staging, service=showcase-service)")
        step("AsyncSmplManagementClient initialized (used only for setup/teardown)")

        # Create demo flags (normally done via Console UI).
        print("  Setting up demo flags...")
        demo_keys = await setup_demo_flags(mgmt)
        print("  Demo flags ready.\n")

        # ==================================================================
        # 1. TYPED FLAG DECLARATIONS
        # ==================================================================
        #
        # Flag declarations are local to the SDK. They do NOT create flags
        # on the server and do NOT trigger lazy initialization.
        #
        # The code-level default is a required keyword argument. It
        # represents "what should this code path do if we can't reach
        # smplkit?" — typically the safe/conservative value.
        #
        # booleanFlag(id, *, default) → BooleanFlag
        # stringFlag(id, *, default)  → StringFlag
        # numberFlag(id, *, default)  → NumberFlag
        # jsonFlag(id, *, default)    → JsonFlag
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
        #
        #   Context(type, key, **attributes)
        #   Context(type, key, attributes_dict)
        #   Context(type, key, attributes_dict, **more_attributes)
        #
        # The SDK uses this for two purposes:
        #   1. Building the nested object for JSON Logic evaluation
        #   2. Registering observed contexts with the server (powers
        #      Console rule builder autocomplete)
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
        step("  Returns: [Context('user', 'user-001', plan='enterprise', ...), ...]")
        step("  JSON Logic sees: {'user': {'key': 'user-001', 'plan': '...'}, 'account': {...}}")

        # ==================================================================
        # 3. EXPLICIT CONTEXT REGISTRATION (Middleware Pattern)
        # ==================================================================
        #
        # In a real application, your middleware registers context on every
        # request — regardless of whether any flags are evaluated. This
        # ensures the Console rule builder always has fresh context data.
        #
        # register() works before lazy initialization. Contexts are queued
        # locally and flushed when the WebSocket is established or
        # flush_contexts() is called.
        # ==================================================================

        section("3. Explicit Context Registration")

        await mgmt.contexts.register(
            [
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
        )
        step("Registered user + account contexts (queued for background flush)")

        # ==================================================================
        # 4. EVALUATE FLAGS — Lazy Init + Local Evaluation
        # ==================================================================
        #
        # The FIRST .get() call triggers lazy initialization:
        #   1. Bulk-fetches all flag definitions (GET /api/v1/flags)
        #   2. Opens the shared WebSocket for live updates
        #   3. Populates the local flag store
        #
        # Subsequent .get() calls are pure local evaluation — no network.
        # There is no connect() call. Initialization is transparent.
        # ==================================================================

        # ------------------------------------------------------------------
        # 4a. Evaluate with current context (Alice, enterprise, US, tech, 500)
        # ------------------------------------------------------------------
        section("4a. Evaluate Flags (Alice — enterprise, US, tech company)")

        # This first .get() triggers lazy initialization behind the scenes.
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
        # 4b. Switch context — simulate a different user/request
        # ------------------------------------------------------------------
        section("4b. Evaluate Flags (Bob — free, EU, retail, 10 employees)")

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
        # 4c. Explicit context override — bypass the provider
        # ------------------------------------------------------------------
        section("4c. Explicit Context Override")

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
        # 5. RESOLUTION CACHING
        # ==================================================================

        section("5. Resolution Caching")

        stats = client.flags.stats()
        step(f"Cache hits so far: {stats.cache_hits}")
        step(f"Cache misses so far: {stats.cache_misses}")

        for _ in range(100):
            checkout_v2.get()

        stats_after = client.flags.stats()
        step(f"Cache hits after 100 reads: {stats_after.cache_hits}")
        assert stats_after.cache_hits >= stats.cache_hits + 100
        step("PASSED — repeated evaluations served from cache ✓")

        # ==================================================================
        # 6. CONTEXT REGISTRATION
        # ==================================================================

        section("6. Context Registration")

        await mgmt.contexts.flush()
        step("Flushed pending context registrations")
        step("Context types, attributes, and values are now available")
        step("in the Console rule builder for autocomplete and suggestions.")

        # ==================================================================
        # 7. REAL-TIME UPDATES — WebSocket + Change Listeners
        # ==================================================================

        section("7. Real-Time Updates via WebSocket")

        # ------------------------------------------------------------------
        # 7a. Register change listeners — @client.flags.on_change decorator
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
        # 7b. Simulate a change via the management API
        # ------------------------------------------------------------------
        step("Adding a rule to banner-color staging via management API...")

        current_banner = await mgmt.flags.get("banner-color")
        current_banner.addRule(
            Rule("Red for small companies")
            .environment("staging")
            .when("account.employee_count", "<", 50)
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
        # 8. SYNC CLIENT DEMO
        # ==================================================================
        section("8. Sync Client (same API, no await)")

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
        #
        #         # First .get() triggers lazy init — no connect() needed
        #         if checkout.get():
        #             render_new_checkout()
        #
        #         # Middleware — register context on every request
        #         mgmt.contexts.register([
        #             Context("user", request.user.id, plan=request.user.plan),
        #         ])

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 9. CLEANUP
        # ==================================================================
        section("9. Cleanup")

        await teardown_demo_flags(mgmt, demo_keys)
        step("Demo flags deleted")

        # ==================================================================
        # DONE
        # ==================================================================
        section("ALL DONE")
        print("  The Flags Runtime showcase completed successfully.")
        print("  If you got here, Smpl Flags is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
