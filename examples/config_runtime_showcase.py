"""
Smpl Config SDK Showcase — Runtime
====================================

Demonstrates the smplkit Python SDK's runtime experience for Smpl Config:

- Prescriptive value resolution via ``client.connect()`` + ``client.config.get()``
- Typed accessors: ``get_str()``, ``get_int()``, ``get_bool()``
- Config inheritance (common → service / module)
- Environment-specific override resolution
- Change listeners: ``client.config.on_change()``
- Manual refresh: ``client.config.refresh()``

This is the SDK experience that 99%% of customers will use. Configs are
created and maintained via the Console UI (or the management API shown
in ``config_management_showcase.py``). This script focuses entirely on
the runtime: connecting, resolving values, and reacting to changes.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The smplkit Config service running and reachable

Usage::

    python examples/config_runtime_showcase.py
"""

import asyncio

from smplkit import AsyncSmplClient

# Demo scaffolding — creates server-side configs so this showcase can
# run standalone. In a real app, configs are created and maintained via
# the Console UI.
from config_runtime_setup import setup_demo_configs, teardown_demo_configs

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
    # 1. SDK INITIALIZATION + SETUP
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
    #       environment="production",
    #       service="showcase-service",
    #   )
    #
    client = AsyncSmplClient(
        environment="production",
        service="showcase-service",
    )
    step("AsyncSmplClient initialized (environment=production, service=showcase-service)")

    # Create server-side state (normally done via Console UI).
    print("  Setting up demo configs...")
    demo = await setup_demo_configs(client)
    print("  Demo configs ready.\n")

    # The server now has:
    #   "common"       — org-wide defaults, with production + staging overrides
    #   "user_service" — service config (inherits from common), with production overrides
    #   "auth_module"  — auth config (inherits from common), with production overrides

    # ======================================================================
    # 2. CONNECT AND READ RESOLVED VALUES
    # ======================================================================
    #
    # client.connect() fetches all configs, resolves values for the
    # environment, and caches everything in-process. After connect(),
    # client.config.get() is a pure local dict read — zero network.
    #
    # ======================================================================

    section("2. Connect and Read Resolved Values")

    await client.connect()
    step("client.connect() completed — all configs fetched and cached")

    # Prescriptive access: get(config_key, item_key)
    db_config = await client.config.get("user_service", "database")
    step(f"database = {db_config}")

    retries = await client.config.get("user_service", "max_retries")
    step(f"max_retries = {retries}")
    # Expected: 5 (inherited from common's production override)

    cache_ttl = await client.config.get("user_service", "cache_ttl_seconds")
    step(f"cache_ttl_seconds = {cache_ttl}")
    # Expected: 600 (user_service production override)

    page_size = await client.config.get("user_service", "pagination_default_page_size")
    step(f"pagination_default_page_size = {page_size}")
    # Expected: 50 (user_service base overrides common's 25)

    missing = await client.config.get("user_service", "nonexistent_key")
    step(f"nonexistent key = {missing}")
    # Expected: None

    # Get all values for a config as a dict
    all_values = await client.config.get("user_service")
    step(f"Total resolved keys for user_service: {len(all_values)}")

    # ======================================================================
    # 3. TYPED ACCESSORS
    # ======================================================================

    section("3. Typed Accessors")

    app_name = await client.config.get_str("user_service", "app_name", default="Unknown")
    step(f"app_name (str) = {app_name}")

    timeout_ms = await client.config.get_int("user_service", "request_timeout_ms", default=3000)
    step(f"request_timeout_ms (int) = {timeout_ms}")

    signup = await client.config.get_bool("user_service", "enable_signup", default=True)
    step(f"enable_signup (bool) = {signup}")
    # Expected: False (production override)

    # ======================================================================
    # 4. INHERITANCE
    # ======================================================================
    #
    # auth_module inherits from common. Values defined in auth_module
    # take precedence; anything not overridden falls through to common.
    #
    # ======================================================================

    section("4. Inheritance (auth_module)")

    session_ttl = await client.config.get("auth_module", "session_ttl_minutes")
    step(f"session_ttl_minutes = {session_ttl}")
    # Expected: 30 (auth_module production override)

    mfa = await client.config.get("auth_module", "mfa_enabled")
    step(f"mfa_enabled = {mfa}")
    # Expected: True (auth_module production override)

    inherited_app = await client.config.get("auth_module", "app_name")
    step(f"app_name (inherited from common) = {inherited_app}")

    # ======================================================================
    # 5. CHANGE LISTENERS AND REFRESH
    # ======================================================================
    #
    # Register callbacks to react when config values change. Then trigger
    # a change via the management API and call refresh() to pick it up.
    #
    # In production, WebSocket events trigger refreshes automatically —
    # no manual refresh() needed.
    #
    # ======================================================================

    section("5a. Change Listeners")

    changes: list = []

    def on_change(event) -> None:
        changes.append(event)
        print(f"    [CHANGE] {event.config_key}.{event.item_key}: {event.old_value!r} -> {event.new_value!r}")

    client.config.on_change(on_change)
    step("Global change listener registered")

    retries_changes: list = []
    client.config.on_change(
        lambda e: retries_changes.append(e),
        config_key="common",
        item_key="max_retries",
    )
    step("Key-specific listener registered for common.max_retries")

    # ------------------------------------------------------------------
    # 5b. Trigger a change via management API, then refresh
    # ------------------------------------------------------------------
    section("5b. Refresh After Management Change")

    common = demo["common"]
    await common.set_value("max_retries", 7, environment="production")
    step("Updated max_retries to 7 on common (production)")

    await client.config.refresh()
    step("client.config.refresh() completed")

    new_retries = await client.config.get("user_service", "max_retries")
    step(f"max_retries after refresh = {new_retries}")
    # Expected: 7

    step(f"Global changes received: {len(changes)}")
    step(f"Retries-specific changes received: {len(retries_changes)}")

    # ======================================================================
    # 6. SYNC CLIENT DEMO
    # ======================================================================
    section("6. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools):
    #
    #     from smplkit import SmplClient
    #
    #     client = SmplClient(environment="production", service="my-service")
    #     client.connect()
    #     host = client.config.get_str("user_service", "database_host")
    #     retries = client.config.get_int("user_service", "max_retries", default=3)
    #     client.config.refresh()  # re-fetch all configs
    #     client.close()

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 7. CLEANUP
    # ======================================================================
    section("7. Cleanup")

    await teardown_demo_configs(client, demo)
    step("Demo configs deleted")

    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Config Runtime showcase completed successfully.")
    print("  If you got here, Smpl Config is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
