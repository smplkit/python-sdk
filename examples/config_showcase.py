"""
Smpl Config SDK Showcase
========================

Demonstrates the smplkit Python SDK for Smpl Config, covering:

- Client initialization (``AsyncSmplClient``)
- Management-plane CRUD: create, update, list, and delete configs
- Environment-specific overrides and multi-level inheritance
- Prescriptive value resolution via ``client.connect()`` + ``client.config.get()``
- Typed accessors: ``get_str()``, ``get_int()``, ``get_bool()``
- Manual refresh: ``client.config.refresh()``
- Change listeners: ``client.config.on_change()``

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
    export SMPLKIT_ENVIRONMENT="production"
    python examples/config_showcase.py
"""

import asyncio
import os
import sys

from smplkit import AsyncSmplClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("SMPLKIT_API_KEY", "")
ENVIRONMENT = os.environ.get("SMPLKIT_ENVIRONMENT", "production")

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
    # Environment is required — it determines how config values are resolved.
    client = AsyncSmplClient(API_KEY, environment=ENVIRONMENT)
    step(f"AsyncSmplClient initialized (environment={ENVIRONMENT})")

    # ======================================================================
    # 2. MANAGEMENT PLANE — Set up the configuration hierarchy
    # ======================================================================

    # ------------------------------------------------------------------
    # 2a. Update the built-in common config
    # ------------------------------------------------------------------
    section("2a. Update the Common Config")

    common = await client.config.get(key="common")
    step(f"Fetched common config: id={common.id}, key={common.key}")

    await common.update(
        description="Organization-wide shared configuration",
        items={
            "app_name": {"value": "Acme SaaS Platform", "type": "STRING"},
            "support_email": {"value": "support@acme.dev", "type": "STRING"},
            "max_retries": {"value": 3, "type": "NUMBER"},
            "request_timeout_ms": {"value": 5000, "type": "NUMBER"},
            "pagination_default_page_size": {"value": 25, "type": "NUMBER"},
        },
    )
    step("Common config base values set")

    await common.set_values(
        {"max_retries": 5, "request_timeout_ms": 10000},
        environment="production",
    )
    step("Common config production overrides set")

    await common.set_values(
        {"max_retries": 2},
        environment="staging",
    )
    step("Common config staging overrides set")

    # ------------------------------------------------------------------
    # 2b. Create a service-specific config (inherits from common)
    # ------------------------------------------------------------------
    section("2b. Create the User Service Config")

    user_service = await client.config.create(
        name="User Service",
        key="user_service",
        description="Configuration for the user microservice.",
        items={
            "database": {"value": {"host": "localhost", "port": 5432, "name": "users_dev", "pool_size": 5}},
            "cache_ttl_seconds": {"value": 300, "type": "NUMBER"},
            "enable_signup": {"value": True, "type": "BOOLEAN"},
            "pagination_default_page_size": {"value": 50, "type": "NUMBER"},
        },
    )
    step(f"Created user_service config: id={user_service.id}")

    await user_service.set_values(
        {
            "database": {"host": "prod-users-rds.internal.acme.dev", "name": "users_prod", "pool_size": 20},
            "cache_ttl_seconds": 600,
        },
        environment="production",
    )
    step("User service production overrides set")

    await user_service.set_value("enable_signup", False, environment="production")
    step("Disabled signup in production")

    # ------------------------------------------------------------------
    # 2c. Create a child config for multi-level inheritance
    # ------------------------------------------------------------------
    section("2c. Create the Auth Module Config (child of User Service)")

    auth_module = await client.config.create(
        name="Auth Module",
        key="auth_module",
        description="Authentication module within the user service.",
        parent=user_service.id,
        items={
            "session_ttl_minutes": {"value": 60, "type": "NUMBER"},
            "mfa_enabled": {"value": False, "type": "BOOLEAN"},
        },
    )
    step(f"Created auth_module config: id={auth_module.id}")

    await auth_module.set_values(
        {"session_ttl_minutes": 30, "mfa_enabled": True},
        environment="production",
    )
    step("Auth module production overrides set")

    # ------------------------------------------------------------------
    # 2d. List all configs
    # ------------------------------------------------------------------
    section("2d. List All Configs")

    configs = await client.config.list()
    for cfg in configs:
        parent_info = f" (parent: {cfg.parent})" if cfg.parent else " (root)"
        step(f"{cfg.key}{parent_info}")

    # ======================================================================
    # 3. PRESCRIPTIVE PLANE — Connect and read resolved values
    # ======================================================================
    #
    # client.connect() fetches all configs, resolves values for the
    # environment, and caches everything in-process. After connect(),
    # client.config.get() is a pure local dict read — zero network.
    #
    # ======================================================================

    section("3a. Connect and Read Resolved Values")

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

    # ------------------------------------------------------------------
    # 3b. Typed accessors
    # ------------------------------------------------------------------
    section("3b. Typed Accessors")

    app_name = await client.config.get_str("user_service", "app_name", default="Unknown")
    step(f"app_name (str) = {app_name}")

    timeout_ms = await client.config.get_int("user_service", "request_timeout_ms", default=3000)
    step(f"request_timeout_ms (int) = {timeout_ms}")

    signup = await client.config.get_bool("user_service", "enable_signup", default=True)
    step(f"enable_signup (bool) = {signup}")
    # Expected: False (production override)

    # ------------------------------------------------------------------
    # 3c. Multi-level inheritance
    # ------------------------------------------------------------------
    section("3c. Multi-Level Inheritance (auth_module)")

    session_ttl = await client.config.get("auth_module", "session_ttl_minutes")
    step(f"session_ttl_minutes = {session_ttl}")
    # Expected: 30 (auth_module production override)

    mfa = await client.config.get("auth_module", "mfa_enabled")
    step(f"mfa_enabled = {mfa}")
    # Expected: True (auth_module production override)

    inherited_app = await client.config.get("auth_module", "app_name")
    step(f"app_name (inherited from common) = {inherited_app}")

    # ======================================================================
    # 4. CHANGE LISTENERS AND REFRESH
    # ======================================================================

    section("4a. Change Listeners")

    changes: list = []

    def on_change(event) -> None:
        changes.append(event)
        print(f"    [CHANGE] {event.config_key}.{event.item_key}: "
              f"{event.old_value!r} -> {event.new_value!r}")

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
    # 4b. Trigger a change via management API, then refresh
    # ------------------------------------------------------------------
    section("4b. Refresh After Management Change")

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
    # 5. SYNC CLIENT DEMO
    # ======================================================================
    section("5. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools):
    #
    #     from smplkit import SmplClient
    #
    #     client = SmplClient("sk_api_...", environment="production")
    #     client.connect()
    #     host = client.config.get_str("user_service", "database_host")
    #     retries = client.config.get_int("user_service", "max_retries", default=3)
    #     client.config.refresh()  # re-fetch all configs
    #     client.close()

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 6. CLEANUP
    # ======================================================================
    section("6. Cleanup")

    await client.config.delete(auth_module.id)
    step(f"Deleted auth_module ({auth_module.id})")

    await client.config.delete(user_service.id)
    step(f"Deleted user_service ({user_service.id})")

    await common.update(description="", items={}, environments={})
    step("Common config reset to empty")

    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Config SDK showcase completed successfully.\n")


if __name__ == "__main__":
    asyncio.run(main())
