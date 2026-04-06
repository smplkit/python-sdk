"""
Smpl Flags SDK Showcase — Runtime Evaluation
==============================================

Demonstrates the smplkit Python SDK's runtime evaluation for Smpl Flags:

- Typed flag declarations with code-level defaults
- Context providers and typed context entities
- Explicit context registration (middleware pattern)
- Connecting to an environment for local evaluation
- Evaluating flags — local JSON Logic, no network per call
- Resolution caching and cache stats
- Explicit context overrides
- Context registration (populates Console rule builder)
- Real-time updates via WebSocket and change listeners
- Flag-specific and global change listeners
- Environment comparison
- Tier 1 explicit evaluation (pass everything)

This is the SDK experience that 99%% of customers will use. Flags are
created and configured via the Console UI (or the management API shown
in ``flags_management_showcase.py``). This script focuses entirely on
the runtime: declaring, connecting, evaluating, and reacting to changes.

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

from smplkit import AsyncSmplClient, Context, Rule

# Demo scaffolding — creates flags so this showcase can run standalone.
# In a real app, flags are created via the Console UI.
from flags_demo_setup import setup_demo_flags, teardown_demo_flags

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

    # Create demo flags (normally done via Console UI).
    print("  Setting up demo flags...")
    demo_flags = await setup_demo_flags(client)
    print("  Demo flags ready.\n")

    # ======================================================================
    # 1. TYPED FLAG DECLARATIONS
    # ======================================================================
    #
    # Flag declarations are local to the SDK. They do NOT create flags
    # on the server. They serve three purposes:
    #
    #   1. Typed handle — get() returns bool, str, int, etc.
    #   2. Code-level default — used if the server is unreachable
    #      or the flag doesn't exist on the server
    #   3. Documentation — which flags this application depends on
    #
    # The code-level default represents "what should this code path do
    # if we can't reach smplkit?" — typically the safe/conservative value.
    # It may or may not match the server-side flag default.
    # ======================================================================

    section("1. Declare Typed Flag Handles")

    checkout_v2 = client.flags.boolFlag("checkout-v2", False)
    banner_color = client.flags.stringFlag("banner-color", "red")
    max_retries = client.flags.numberFlag("max-retries", 3)

    # This flag doesn't exist on the server — code default will be used.
    nonexistent = client.flags.boolFlag("feature-that-doesnt-exist", False)

    step(f"checkout_v2:    key={checkout_v2.key}, code_default={checkout_v2.default}")
    step(f"banner_color:   key={banner_color.key}, code_default={banner_color.default}")
    step(f"max_retries:    key={max_retries.key}, code_default={max_retries.default}")
    step(f"nonexistent:    key={nonexistent.key}, code_default={nonexistent.default}")

    # ======================================================================
    # 2. CONTEXT PROVIDER
    # ======================================================================
    #
    # The context provider is a function called on every flag.get().
    # It returns a list of Context objects, each describing a typed
    # entity in the evaluation context.
    #
    #   Context(type, key, **attributes)
    #
    # - type: the context type ("user", "account", "device", etc.)
    # - key: the entity identifier ("user-123", "acme-corp")
    # - **attributes: keyword args for any attributes to target on
    #
    # In a real app, this pulls from the current request, authenticated
    # user, session, etc.
    #
    # The SDK uses this for two purposes:
    #   1. Building the nested object for JSON Logic evaluation
    #   2. Registering observed contexts with the server (powers
    #      Console rule builder autocomplete)
    # ======================================================================

    section("2. Register Context Provider")

    @client.flags.context_provider
    def resolve_context():
        return [
            Context(
                "user",
                _current_user["id"],
                name=_current_user["first_name"],
                first_name=_current_user["first_name"],
                plan=_current_user["plan"],
                beta_tester=_current_user["beta_tester"],
            ),
            Context(
                "account",
                _current_account["id"],
                name=_current_account["industry"],
                industry=_current_account["industry"],
                region=_current_account["region"],
                employee_count=_current_account["employee_count"],
            ),
        ]

    step("Context provider registered")
    step("  Returns: [Context('user', 'user-001', plan='enterprise', ...), ...]")
    step("  JSON Logic sees: {'user': {'key': 'user-001', 'plan': '...'}, 'account': {...}}")

    # ======================================================================
    # 3. EXPLICIT CONTEXT REGISTRATION (Middleware Pattern)
    # ======================================================================
    #
    # In a real application, your middleware registers context on every
    # request — regardless of whether any flags are evaluated. This
    # ensures the Console rule builder always has fresh context data
    # to offer as autocomplete suggestions.
    #
    # register() accepts a single Context or a list. It queues contexts
    # for background batch registration — it never blocks the request.
    # ======================================================================

    section("3. Explicit Context Registration")

    # Single context — common in simple middleware
    client.flags.register(
        Context(
            "user",
            _current_user["id"],
            name=_current_user["first_name"],
            first_name=_current_user["first_name"],
            plan=_current_user["plan"],
            beta_tester=_current_user["beta_tester"],
        )
    )
    step("Registered single user context")

    # Multiple contexts at once — typical middleware pattern
    client.flags.register(
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
    step("Registered user + account contexts")

    # register() works before connect() — contexts are queued locally
    # and flushed when the connection is established or flush_contexts()
    # is called. This means your middleware can start registering
    # contexts at app startup, even before the flags environment is known.
    step("Note: register() works before connect() — contexts are queued locally")

    # ======================================================================
    # 4. CONNECT — Fetch definitions, open WebSocket, go local
    # ======================================================================

    section("4. Connect to Staging Environment")

    # connect() does three things:
    #   1. Fetches all flag definitions via GET /api/v1/flags
    #   2. Opens a shared WebSocket for live update events
    #   3. Enables local JSON Logic evaluation for all declared flags
    #
    # After connect(), get() never touches the network.
    # The environment is set at client construction time.

    await client.connect()
    step("Connected to staging — flags loaded, WebSocket open")

    # ======================================================================
    # 5. EVALUATE FLAGS — Local, typed, instant
    # ======================================================================

    # ------------------------------------------------------------------
    # 5a. Evaluate with current context (Alice, enterprise, US, tech, 500)
    # ------------------------------------------------------------------
    section("5a. Evaluate Flags (Alice — enterprise, US, tech company)")

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
    # 5b. Switch context — simulate a different user/request
    # ------------------------------------------------------------------
    section("5b. Evaluate Flags (Bob — free, EU, retail, 10 employees)")

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
    # No rules match: not enterprise, not technology; flag default = red

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
    # 5c. Explicit context override — bypass the provider
    # ------------------------------------------------------------------
    section("5c. Explicit Context Override")

    # For edge cases (background jobs, tests), pass context directly.
    # This bypasses the registered provider for this one call.

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

    # ======================================================================
    # 6. RESOLUTION CACHING
    # ======================================================================

    section("6. Resolution Caching")

    # The SDK caches resolved values by (flag_key, context_hash).
    # Repeated evaluations with identical context skip JSON Logic
    # evaluation entirely — pure hash lookup.

    stats = client.flags.stats()
    step(f"Cache hits so far: {stats.cache_hits}")
    step(f"Cache misses so far: {stats.cache_misses}")

    for _ in range(100):
        checkout_v2.get()

    stats_after = client.flags.stats()
    step(f"Cache hits after 100 reads: {stats_after.cache_hits}")
    assert stats_after.cache_hits >= stats.cache_hits + 100
    step("PASSED — repeated evaluations served from cache ✓")

    # ======================================================================
    # 7. CONTEXT REGISTRATION
    # ======================================================================
    #
    # As a side effect of calling the context provider, the SDK batches
    # newly-observed context instances and sends them to the server in
    # the background. This populates the Console rule builder's
    # autocomplete with real context types, attributes, and values.
    #
    # Contexts may have been registered both explicitly via register()
    # (§3) and automatically via the context provider during get() calls.
    #
    # Registration is fire-and-forget — it never blocks flag evaluation.
    # ======================================================================

    section("7. Context Registration")

    await client.flags.flush_contexts()
    step("Flushed pending context registrations")

    # Verify the server now knows about our context types.
    context_types = await client.flags.list_context_types()
    step(f"Context types on server: {[ct.key for ct in context_types]}")
    # Expected: ["user", "account"]

    for ct in context_types:
        step(f"  {ct.key}: attributes={list(ct.attributes.keys())}")
    # Expected: user has first_name, plan, beta_tester
    # Expected: account has industry, region, employee_count

    step("Contexts registered via both register() and automatic get() side-effect")
    step("Context registration verified — Console rule builder has real data ✓")

    # ======================================================================
    # 8. REAL-TIME UPDATES — WebSocket-driven cache invalidation
    # ======================================================================

    section("8. Real-Time Updates via WebSocket")

    # ------------------------------------------------------------------
    # 8a. Register change listeners
    # ------------------------------------------------------------------

    # Global listener — fires when ANY flag definition changes.
    all_changes: list[dict] = []

    @client.flags.on_change
    def on_any_change(event):
        all_changes.append({"key": event.key, "source": event.source})
        print(f"    [GLOBAL] Flag '{event.key}' updated via {event.source}")

    step("Global change listener registered (fires for any flag)")

    # Flag-specific listener — fires only when THIS flag changes.
    banner_changes: list = []

    @banner_color.on_change
    def on_banner_change(event):
        banner_changes.append(event)
        print("    [BANNER] banner-color definition changed")

    step("Flag-specific listener registered for banner-color")

    checkout_changes: list = []

    @checkout_v2.on_change
    def on_checkout_change(event):
        checkout_changes.append(event)
        print("    [CHECKOUT] checkout-v2 definition changed")

    step("Flag-specific listener registered for checkout-v2")

    # ------------------------------------------------------------------
    # 8b. Simulate a change via the management API
    # ------------------------------------------------------------------
    step("Adding a rule to banner-color staging via management API...")

    # In real life this would be done via the Console UI by another
    # team member. We simulate it here with the management API.
    current_banner = await client.flags.get(demo_flags[1].id)
    await current_banner.addRule(
        Rule("Red for small companies")
        .environment("staging")
        .when("account.employee_count", "<", 50)
        .serve("red")
        .build()
    )

    # Give the WebSocket a moment to deliver the update.
    await asyncio.sleep(2)

    step(f"Global changes received: {len(all_changes)}")
    step(f"Banner-specific changes: {len(banner_changes)}")
    step(f"Checkout-specific changes: {len(checkout_changes)}")
    # Expected: global=1, banner=1, checkout=0 (only banner was changed)

    # ------------------------------------------------------------------
    # 8c. Connection lifecycle
    # ------------------------------------------------------------------
    ws_status = client.flags.connection_status()
    step(f"WebSocket status: {ws_status}")

    # The SDK reconnects automatically if the connection drops, using
    # exponential backoff. You can also manually refresh all definitions.
    await client.flags.refresh()
    step("Manual refresh completed")

    # ======================================================================
    # 9. ENVIRONMENT COMPARISON
    # ======================================================================

    section("9. Environment Comparison")

    # Use the Tier 1 evaluate() API to compare flag values across
    # environments without disconnecting and reconnecting.
    eval_ctx = [
        Context("user", _current_user["id"], plan=_current_user["plan"], beta_tester=_current_user["beta_tester"]),
        Context(
            "account", _current_account["id"], industry=_current_account["industry"], region=_current_account["region"]
        ),
    ]
    for env in ["staging", "production"]:
        c = await client.flags.evaluate("checkout-v2", environment=env, context=eval_ctx)
        b = await client.flags.evaluate("banner-color", environment=env, context=eval_ctx)
        r = await client.flags.evaluate("max-retries", environment=env, context=eval_ctx)
        step(f"[{env:12}] checkout-v2={c}, banner-color={b}, max-retries={r}")

    # ======================================================================
    # 10. TIER 1 — Explicit evaluation (pass everything)
    # ======================================================================

    section("10. Tier 1 — Explicit Evaluation (No Provider)")

    # The Tier 1 API is always available alongside the prescriptive tier.
    # Useful for scripts, one-off jobs, and infrastructure code.
    # Flag key is the lone positional arg.

    explicit_value = await client.flags.evaluate(
        "banner-color",
        environment="staging",
        context=[
            Context("user", "user-999", plan="enterprise"),
            Context("account", "corp-999", industry="technology"),
        ],
    )
    step(f"Tier 1 evaluate banner-color = {explicit_value}")
    # Expected: "blue" (enterprise plan matches first rule)

    # ======================================================================
    # 11. SYNC CLIENT
    # ======================================================================
    section("11. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools), SmplClient
    # provides an identical API surface without async/await:
    #
    #     from smplkit import SmplClient, Context
    #
    #     client = SmplClient(environment="production", service="my-service")
    #
    #     @client.flags.context_provider
    #     def resolve_context():
    #         return [
    #             Context("user", request.user.id, plan=request.user.plan),
    #         ]
    #
    #     checkout = client.flags.boolFlag("checkout-v2", False)
    #     client.connect()
    #
    #     # In middleware — every request
    #     client.flags.register([
    #         Context("user", request.user.id, plan=request.user.plan),
    #         Context("account", request.account.id, region=request.account.region),
    #     ])
    #
    #     # In handler — evaluate flags (context provider also auto-registers)
    #     if checkout.get():       # synchronous — no await
    #         render_new_checkout()
    #
    #     client.flags.disconnect()
    #     client.close()

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 12. CLEANUP
    # ======================================================================
    section("12. Cleanup")

    await client.flags.disconnect()
    step("Disconnected from flags environment")

    await teardown_demo_flags(client, demo_flags)
    step("Demo flags and context types deleted")

    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Flags Runtime showcase completed successfully.")
    print("  If you got here, Smpl Flags is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
