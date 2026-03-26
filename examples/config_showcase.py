"""
Smpl Config SDK Showcase
========================

Demonstrates the smplkit Python SDK for Smpl Config, covering:

- Client initialization (``AsyncSmplClient``)
- Management-plane CRUD: create, update, list, and delete configs
- Environment-specific overrides and multi-level inheritance
- Runtime value resolution: ``connect()``, ``get()``, typed accessors
- Real-time updates via WebSocket and change listeners
- Manual refresh and cache diagnostics
- Async context manager pattern for automatic cleanup

This script is designed to be read top-to-bottom as a walkthrough of the
SDK's full capability surface. It is runnable against a live smplkit
environment, but is *not* a test — it creates, modifies, and deletes
real configs.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key (set via ``SMPLKIT_API_KEY`` env var)
    - The smplkit Config service running and reachable

Usage::

    export SMPLKIT_API_KEY="sk_api_..."
    python examples/config_showcase.py
"""

import asyncio
import os
import sys
import time

from smplkit import AsyncSmplClient

# ---------------------------------------------------------------------------
# Configuration — set your API key via the SMPLKIT_API_KEY env var
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("SMPLKIT_API_KEY", "")

if not API_KEY:
    print("ERROR: Set the SMPLKIT_API_KEY environment variable before running.")
    print("  export SMPLKIT_API_KEY='sk_api_...'")
    sys.exit(1)

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

    # The AsyncSmplClient is the entry point for async applications.
    # Sync applications use SmplClient instead — identical API surface
    # but without await on management methods.  API key is the only
    # required argument.
    client = AsyncSmplClient(API_KEY)
    step("AsyncSmplClient initialized")

    # ======================================================================
    # 2. MANAGEMENT PLANE — Set up the configuration hierarchy
    # ======================================================================
    #
    # This section uses the management API to create and populate configs.
    # In real life, a customer might do this via the console UI, Terraform,
    # or a setup script. The SDK supports all of it programmatically.
    # ======================================================================

    # ------------------------------------------------------------------
    # 2a. Update the built-in common config
    # ------------------------------------------------------------------
    section("2a. Update the Common Config")

    # Every account has a 'common' config auto-created at provisioning.
    # It serves as the default parent for all other configs. Let's populate
    # it with shared baseline values that every service in our org needs.

    common = await client.config.get(key="common")
    step(f"Fetched common config: id={common.id}, key={common.key}")

    # Set base values — these apply to ALL environments by default.
    await common.update(
        description="Organization-wide shared configuration",
        values={
            "app_name": "Acme SaaS Platform",
            "support_email": "support@acme.dev",
            "max_retries": 3,
            "request_timeout_ms": 5000,
            "pagination_default_page_size": 25,
            "credentials": {
                "oauth_provider": "https://auth.acme.dev",
                "client_id": "acme_default_client",
                "scopes": ["read"],
            },
            "feature_flags": {
                "provider": "smplkit",
                "endpoint": "https://flags.smplkit.com",
                "refresh_interval_seconds": 30,
            },
        },
    )
    step("Common config base values set")

    # Override specific values for production — these flow through to every
    # config that inherits from common, unless overridden further down.
    await common.set_values(
        {
            "max_retries": 5,
            "request_timeout_ms": 10000,
            "credentials": {
                "scopes": ["read", "write", "admin"],
            },
        },
        environment="production",
    )
    step("Common config production overrides set")

    # Staging gets its own tweaks.
    await common.set_values(
        {
            "max_retries": 2,
            "credentials": {
                "scopes": ["read", "write"],
            },
        },
        environment="staging",
    )
    step("Common config staging overrides set")

    # ------------------------------------------------------------------
    # 2b. Create a service-specific config (inherits from common)
    # ------------------------------------------------------------------
    section("2b. Create the User Service Config")

    # When we don't specify a parent, the API defaults to common.
    # This config adds service-specific keys and overrides a few common ones.
    user_service = await client.config.create(
        name="User Service",
        key="user_service",
        description="Configuration for the user microservice and its dependencies.",
        values={
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "users_dev",
                "pool_size": 5,
                "ssl_mode": "prefer",
            },
            "cache_ttl_seconds": 300,
            "enable_signup": True,
            "allowed_email_domains": ["acme.dev", "acme.com"],
            # Override the common pagination default for this service
            "pagination_default_page_size": 50,
        },
    )
    step(f"Created user_service config: id={user_service.id}")

    # Production overrides for the user service.
    await user_service.set_values(
        {
            "database": {
                "host": "prod-users-rds.internal.acme.dev",
                "name": "users_prod",
                "pool_size": 20,
                "ssl_mode": "require",
            },
            "cache_ttl_seconds": 600,
        },
        environment="production",
    )
    step("User service production overrides set")

    # Staging overrides.
    await user_service.set_values(
        {
            "database": {
                "host": "staging-users-rds.internal.acme.dev",
                "name": "users_staging",
                "pool_size": 10,
            },
        },
        environment="staging",
    )
    step("User service staging overrides set")

    # Add keys that only exist in the development environment.
    await user_service.set_values(
        {
            "debug_sql": True,
            "seed_test_data": True,
        },
        environment="development",
    )
    step("User service development-only keys set")

    # Set a single value using the convenience method.
    await user_service.set_value("enable_signup", False, environment="production")
    step("Disabled signup in production via set_value")

    # ------------------------------------------------------------------
    # 2c. Create a second config to show multi-level inheritance
    # ------------------------------------------------------------------
    section("2c. Create the Auth Module Config (child of User Service)")

    # This config's parent is user_service (not common), demonstrating
    # multi-level inheritance: auth_module → user_service → common.
    auth_module = await client.config.create(
        name="Auth Module",
        key="auth_module",
        description="Authentication module within the user service.",
        parent=user_service.id,
        values={
            "session_ttl_minutes": 60,
            "max_failed_attempts": 5,
            "lockout_duration_minutes": 15,
            "mfa_enabled": False,
        },
    )
    step(f"Created auth_module config: id={auth_module.id}, parent={user_service.id}")

    await auth_module.set_values(
        {
            "session_ttl_minutes": 30,
            "mfa_enabled": True,
            "max_failed_attempts": 3,
        },
        environment="production",
    )
    step("Auth module production overrides set")

    # ------------------------------------------------------------------
    # 2d. List all configs — verify hierarchy
    # ------------------------------------------------------------------
    section("2d. List All Configs")

    configs = await client.config.list()
    for cfg in configs:
        parent_info = f" (parent: {cfg.parent})" if cfg.parent else " (root)"
        step(f"{cfg.key}{parent_info}")

    # ======================================================================
    # 3. RUNTIME PLANE — Resolve configuration in a running application
    # ======================================================================
    #
    # This is the heart of the SDK experience. A customer's application
    # connects to a config for a specific environment, and the SDK:
    #
    #   - Eagerly fetches the config and its entire parent chain
    #   - Resolves values via deep merge (inheritance + env overrides)
    #   - Caches everything in-process — get() is a local dict read
    #   - Maintains a WebSocket for real-time server-pushed updates
    #   - Notifies registered listeners when values change
    #
    # get() and all value-access methods are SYNCHRONOUS. They never
    # touch the network. The only async operations are connect(),
    # refresh(), and close().
    #
    # ======================================================================

    # ------------------------------------------------------------------
    # 3a. Connect to a config for runtime use
    # ------------------------------------------------------------------
    section("3a. Connect to Runtime Config")

    # connect() eagerly fetches the config and its full parent chain,
    # resolves all values for the given environment, and establishes
    # a WebSocket connection for real-time updates. When it returns,
    # the cache is fully populated and ready.
    #
    # The timeout controls how long to wait for the initial fetch.
    # If it expires, connect() raises SmplTimeoutError.

    runtime = await user_service.connect("production", timeout=10)
    step("Runtime config connected and fully loaded")

    # ------------------------------------------------------------------
    # 3b. Read resolved values — all synchronous, all from local cache
    # ------------------------------------------------------------------
    section("3b. Read Resolved Values")

    db_config = runtime.get("database")
    step(f"database = {db_config}")
    # Expected (deep-merged): user_service prod override + user_service base
    # {
    #     "host": "prod-users-rds.internal.acme.dev",
    #     "port": 5432,                          ← inherited from base
    #     "name": "users_prod",
    #     "pool_size": 20,
    #     "ssl_mode": "require",
    # }

    retries = runtime.get("max_retries")
    step(f"max_retries = {retries}")
    # Expected: 5 (from common's production override — inherited through)

    creds = runtime.get("credentials")
    step(f"credentials = {creds}")

    cache_ttl = runtime.get("cache_ttl_seconds")
    step(f"cache_ttl_seconds = {cache_ttl}")
    # Expected: 600 (user_service production override)

    page_size = runtime.get("pagination_default_page_size")
    step(f"pagination_default_page_size = {page_size}")
    # Expected: 50 (user_service base overrides common's 25)

    support = runtime.get("support_email")
    step(f"support_email = {support}")
    # Expected: "support@acme.dev" (inherited all the way from common base)

    missing = runtime.get("this_key_does_not_exist")
    step(f"nonexistent key = {missing}")
    # Expected: None

    with_default = runtime.get("this_key_does_not_exist", default="fallback")
    step(f"nonexistent key with default = {with_default}")
    # Expected: "fallback"

    # Typed convenience accessors for common JSON types.
    signup_enabled = runtime.get_bool("enable_signup", default=False)
    step(f"enable_signup (bool) = {signup_enabled}")
    # Expected: False (user_service production override via set_value)

    timeout_ms = runtime.get_int("request_timeout_ms", default=3000)
    step(f"request_timeout_ms (int) = {timeout_ms}")
    # Expected: 10000 (common production override)

    app_name = runtime.get_str("app_name", default="Unknown")
    step(f"app_name (str) = {app_name}")
    # Expected: "Acme SaaS Platform" (common base)

    # Check whether a key exists (regardless of its value).
    step(f"'database' exists = {runtime.exists('database')}")
    # Expected: True
    step(f"'ghost_key' exists = {runtime.exists('ghost_key')}")
    # Expected: False

    # ------------------------------------------------------------------
    # 3c. Verify local caching — no network requests on repeated reads
    # ------------------------------------------------------------------
    section("3c. Verify Local Caching")

    # connect() fetched everything eagerly. All get() calls are pure
    # local dict reads with zero network overhead. The stats object
    # lets us verify this.

    stats = runtime.stats()
    step(f"Network fetches so far: {stats.fetch_count}")
    # Expected: 2 (user_service + common, fetched during connect)

    # Read a bunch of keys — none should trigger a fetch.
    for _ in range(100):
        runtime.get("max_retries")
        runtime.get("database")
        runtime.get("credentials")

    stats_after = runtime.stats()
    step(f"Network fetches after 300 reads: {stats_after.fetch_count}")
    # Expected: still 2
    assert stats_after.fetch_count == stats.fetch_count, (
        f"SDK made unexpected network calls! "
        f"Before: {stats.fetch_count}, After: {stats_after.fetch_count}"
    )
    step("PASSED — all reads served from local cache")

    # ------------------------------------------------------------------
    # 3d. Get ALL resolved values as a dictionary
    # ------------------------------------------------------------------
    section("3d. Get Full Resolved Configuration")

    # Sometimes you want the entire resolved config as a dict — for
    # logging at startup, passing to a framework, or debugging.
    all_values = runtime.get_all()
    step(f"Total resolved keys: {len(all_values)}")
    for key in sorted(all_values.keys()):
        step(f"  {key} = {all_values[key]}")

    # ------------------------------------------------------------------
    # 3e. Multi-level inheritance — connect to auth_module in production
    # ------------------------------------------------------------------
    section("3e. Multi-Level Inheritance (auth_module)")

    async with auth_module.connect("production", timeout=10) as auth_runtime:
        session_ttl = auth_runtime.get("session_ttl_minutes")
        step(f"session_ttl_minutes = {session_ttl}")
        # Expected: 30 (auth_module production override)

        mfa = auth_runtime.get("mfa_enabled")
        step(f"mfa_enabled = {mfa}")
        # Expected: True (auth_module production override)

        # Keys inherited from user_service:
        db = auth_runtime.get("database")
        step(f"database (inherited from user_service) = {db}")

        # Keys inherited all the way from common:
        app = auth_runtime.get("app_name")
        step(f"app_name (inherited from common) = {app}")

    step("auth_runtime closed via context manager")

    # ======================================================================
    # 4. REAL-TIME UPDATES — WebSocket-driven cache invalidation
    # ======================================================================
    #
    # The SDK maintains a WebSocket connection to the config service. When
    # a config value is changed (via the console, API, or another SDK
    # instance), the server pushes an update and the SDK refreshes its
    # local cache. The application can register listeners to react to
    # changes without polling.
    # ======================================================================

    section("4. Real-Time Updates via WebSocket")

    # ------------------------------------------------------------------
    # 4a. Register a change listener
    # ------------------------------------------------------------------

    changes_received: list[dict] = []

    def on_change(event) -> None:
        """Called whenever a config value changes for our config+environment."""
        changes_received.append({
            "key": event.key,
            "old_value": event.old_value,
            "new_value": event.new_value,
            "source": event.source,  # "websocket" | "poll" | "manual"
        })
        print(f"    [CHANGE] {event.key}: {event.old_value!r} → {event.new_value!r}")

    runtime.on_change(on_change)
    step("Change listener registered")

    # You can also listen for changes to a specific key.
    retry_changes: list = []
    runtime.on_change(lambda e: retry_changes.append(e), key="max_retries")
    step("Key-specific listener registered for 'max_retries'")

    # ------------------------------------------------------------------
    # 4b. Simulate a config change via the management API
    # ------------------------------------------------------------------
    step("Updating max_retries on common (production) via management API...")

    await common.set_value("max_retries", 7, environment="production")

    # Give the WebSocket a moment to deliver the update.
    await asyncio.sleep(2)

    # The runtime cache should now reflect the new value WITHOUT us
    # having to do anything — the WebSocket pushed the update.
    new_retries = runtime.get("max_retries")
    step(f"max_retries after live update = {new_retries}")
    # Expected: 7

    step(f"Changes received by listener: {len(changes_received)}")
    step(f"Retry-specific changes received: {len(retry_changes)}")

    # ------------------------------------------------------------------
    # 4c. Connection lifecycle
    # ------------------------------------------------------------------
    section("4c. WebSocket Connection Lifecycle")

    ws_status = runtime.connection_status()
    step(f"WebSocket status: {ws_status}")
    # Expected: "connected"

    # The SDK reconnects automatically if the connection drops, using
    # exponential backoff (1s, 2s, 4s, ... capped at 60s, retries forever).
    # You can also manually force a refresh if needed.
    await runtime.refresh()
    step("Manual refresh completed")

    # ======================================================================
    # 5. ENVIRONMENT COMPARISON
    # ======================================================================

    section("5. Environment Comparison")

    # A developer might want to see how the same config resolves across
    # environments — useful for debugging "works in staging but not prod."

    for env in ["development", "staging", "production"]:
        async with user_service.connect(env, timeout=10) as env_runtime:
            db_host = env_runtime.get("database", default={}).get("host", "N/A")
            retries = env_runtime.get("max_retries")
            step(f"[{env:12}] db.host={db_host}, retries={retries}")

    # ======================================================================
    # 6. SYNC CLIENT DEMO
    # ======================================================================
    section("6. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools, scripts), SmplClient
    # provides an identical API surface without async/await:
    #
    #     from smplkit import SmplClient
    #
    #     client = SmplClient("sk_api_...")
    #     config = client.config.get(key="user_service")
    #     config.set_values({"max_retries": 10}, environment="production")
    #     runtime = config.connect("production", timeout=10)
    #     retries = runtime.get("max_retries")  # still sync — same as async
    #     runtime.close()
    #
    # ConfigRuntime.get() and all value-access methods are always
    # synchronous regardless of which client created the runtime.

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 7. CLEANUP
    # ======================================================================
    section("7. Cleanup")

    # Close the runtime connection (WebSocket teardown).
    await runtime.close()
    step("Runtime connection closed")

    # Delete configs in dependency order (children first).
    await client.config.delete(auth_module.id)
    step(f"Deleted auth_module ({auth_module.id})")

    await client.config.delete(user_service.id)
    step(f"Deleted user_service ({user_service.id})")

    # Restore common to empty state (can't delete, but can clear values).
    await common.update(
        description="",
        values={},
        environments={},
    )
    step("Common config reset to empty")

    # Close the SDK client (cleans up HTTP connection pools).
    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Config SDK showcase completed successfully.")
    print("  If you got here, Smpl Config is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
