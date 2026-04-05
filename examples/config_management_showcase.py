"""
Smpl Config SDK Showcase — Management API
===========================================

Demonstrates the smplkit Python SDK's management plane for Smpl Config:

- Config CRUD: create, get, list, update, and delete configs
- Base values and environment-specific overrides
- Multi-level inheritance via parent configs
- Set and clear individual values
- Listing all configs

Most customers will manage configs via the Console UI. This showcase
demonstrates the programmatic equivalent — useful for infrastructure-
as-code, CI/CD pipelines, setup scripts, and automated testing.

For the runtime experience (connect, prescriptive resolution, typed
accessors, change listeners), see ``config_runtime_showcase.py``.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key (set via ``SMPLKIT_API_KEY`` env var)
    - The smplkit Config service running and reachable

Usage::

    export SMPLKIT_API_KEY="sk_api_..."
    export SMPLKIT_ENVIRONMENT="production"
    python examples/config_management_showcase.py
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

    # Management operations do not require connect() — they are
    # stateless API calls.
    client = AsyncSmplClient(API_KEY, environment=ENVIRONMENT)
    step(f"AsyncSmplClient initialized (environment={ENVIRONMENT})")

    # ======================================================================
    # 2. UPDATE THE BUILT-IN COMMON CONFIG
    # ======================================================================
    #
    # Every organization has a built-in "common" config that serves as
    # the root of the inheritance hierarchy. Update it with org-wide
    # defaults.
    #
    # ======================================================================

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

    # ------------------------------------------------------------------
    # 2b. Environment overrides
    # ------------------------------------------------------------------
    section("2b. Environment Overrides on Common")

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

    # ======================================================================
    # 3. CREATE SERVICE-SPECIFIC CONFIGS
    # ======================================================================

    # ------------------------------------------------------------------
    # 3a. Create a service config (inherits from common)
    # ------------------------------------------------------------------
    section("3a. Create the User Service Config")

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
    # 3b. Create a child config (multi-level inheritance)
    # ------------------------------------------------------------------
    section("3b. Create the Auth Module Config (child of User Service)")

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

    # ======================================================================
    # 4. LIST AND INSPECT CONFIGS
    # ======================================================================

    # ------------------------------------------------------------------
    # 4a. List all configs
    # ------------------------------------------------------------------
    section("4a. List All Configs")

    configs = await client.config.list()
    for cfg in configs:
        parent_info = f" (parent: {cfg.parent})" if cfg.parent else " (root)"
        step(f"{cfg.key}{parent_info}")

    # ------------------------------------------------------------------
    # 4b. Get a single config by ID
    # ------------------------------------------------------------------
    section("4b. Get a Config by ID")

    fetched = await client.config.get(id=user_service.id)
    step(f"Fetched: key={fetched.key}, name={fetched.name}")
    step(f"  description={fetched.description}")
    step(f"  parent={fetched.parent or '(none)'}")

    # ======================================================================
    # 5. UPDATE A CONFIG
    # ======================================================================

    section("5. Update a Config")

    await user_service.update(
        description="User microservice — updated description",
    )
    step(f"Updated user_service description")

    await user_service.set_value("cache_ttl_seconds", 900, environment="production")
    step("Updated production cache_ttl_seconds: 600 → 900")

    # ======================================================================
    # 6. SYNC CLIENT DEMO
    # ======================================================================
    section("6. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools):
    #
    #     from smplkit import SmplClient
    #
    #     client = SmplClient("sk_api_...", environment="production")
    #
    #     # Management API (no connect() needed)
    #     common = client.config.get(key="common")
    #     common.update(items={"key": {"value": "val", "type": "STRING"}})
    #
    #     svc = client.config.create(name="My Service", key="my_svc", items={...})
    #     svc.set_values({"key": "val"}, environment="production")
    #
    #     configs = client.config.list()
    #
    #     client.config.delete(svc.id)
    #     client.close()

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 7. CLEANUP
    # ======================================================================
    section("7. Cleanup")

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
    print("  The Config Management showcase completed successfully.")
    print("  All configs have been cleaned up.\n")


if __name__ == "__main__":
    asyncio.run(main())
