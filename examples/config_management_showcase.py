"""
Smpl Config SDK Showcase — Management API
===========================================

Demonstrates the smplkit Python SDK's management plane for Smpl Config:

- Config CRUD: new() + save(), get(key), list(), delete(key)
- Active record pattern: fetch → mutate → save()
- Base items and environment-specific overrides
- Config inheritance from the common root

Most customers will manage configs via the Console UI. This showcase
demonstrates the programmatic equivalent — useful for infrastructure-
as-code, CI/CD pipelines, setup scripts, and automated testing.

For the runtime experience (resolve, subscribe, change listeners),
see ``config_runtime_showcase.py``.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The smplkit Config service running and reachable

Usage::

    python examples/config_management_showcase.py
"""

import asyncio

from smplkit import AsyncSmplClient

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

    # Management operations do not require connect() or lazy init — they
    # are stateless HTTP calls that bypass the runtime cache entirely.
    async with AsyncSmplClient(environment="production", service="showcase-service") as client:

        step("AsyncSmplClient initialized (environment=production, service=showcase-service)")

        # Clean up leftover configs from previous runs (order matters: children first).
        for leftover_key in ("auth_module", "user_service"):
            try:
                await client.config.delete(leftover_key)
            except Exception:
                pass

        # ==================================================================
        # 2. UPDATE THE BUILT-IN COMMON CONFIG
        # ==================================================================
        #
        # Every organization has a built-in "common" config that serves as
        # the root of the inheritance hierarchy. Fetch it, mutate it, save.
        # ==================================================================

        section("2a. Update the Common Config")

        common = await client.config.get("common")
        step(f"Fetched common config: id={common.id}, key={common.key}")

        # Mutate items — local until save()
        common.items = {
            "app_name": {"value": "Acme SaaS Platform", "type": "STRING"},
            "support_email": {"value": "support@acme.dev", "type": "STRING"},
            "max_retries": {"value": 3, "type": "NUMBER"},
            "request_timeout_ms": {"value": 5000, "type": "NUMBER"},
            "pagination_default_page_size": {"value": 25, "type": "NUMBER"},
        }
        common.description = "Organization-wide shared configuration"
        await common.save()
        step("Common config base values set")

        # ------------------------------------------------------------------
        # 2b. Environment overrides — mutate environments dict, then save
        # ------------------------------------------------------------------
        section("2b. Environment Overrides on Common")

        common.environments = {
            "production": {
                "values": {
                    "max_retries": {"value": 5},
                    "request_timeout_ms": {"value": 10000},
                },
            },
            "staging": {
                "values": {
                    "max_retries": {"value": 2},
                },
            },
        }
        await common.save()
        step("Common config production + staging overrides set")

        # ==================================================================
        # 3. CREATE SERVICE-SPECIFIC CONFIGS
        # ==================================================================

        # ------------------------------------------------------------------
        # 3a. Create a service config (inherits from common)
        # ------------------------------------------------------------------
        section("3a. Create the User Service Config")

        user_service = client.config.new(
            "user_service",
            name="User Service",
            description="Configuration for the user microservice.",
        )
        # Set items — local mutation
        user_service.items = {
            "database.host": {"value": "localhost", "type": "STRING"},
            "database.port": {"value": 5432, "type": "NUMBER"},
            "database.name": {"value": "users_dev", "type": "STRING"},
            "database.pool_size": {"value": 5, "type": "NUMBER"},
            "cache_ttl_seconds": {"value": 300, "type": "NUMBER"},
            "enable_signup": {"value": True, "type": "BOOLEAN"},
            "pagination_default_page_size": {"value": 50, "type": "NUMBER"},
        }
        user_service.environments = {
            "production": {
                "values": {
                    "database.host": {"value": "prod-users-rds.internal.acme.dev"},
                    "database.name": {"value": "users_prod"},
                    "database.pool_size": {"value": 20},
                    "cache_ttl_seconds": {"value": 600},
                    "enable_signup": {"value": False},
                },
            },
        }
        await user_service.save()
        step(f"Created user_service config: id={user_service.id}")

        # ------------------------------------------------------------------
        # 3b. Create the auth module config (inherits from common)
        # ------------------------------------------------------------------
        section("3b. Create the Auth Module Config")

        auth_module = client.config.new(
            "auth_module",
            name="Auth Module",
            description="Authentication module within the user service.",
        )
        auth_module.items = {
            "session_ttl_minutes": {"value": 60, "type": "NUMBER"},
            "mfa_enabled": {"value": False, "type": "BOOLEAN"},
        }
        auth_module.environments = {
            "production": {
                "values": {
                    "session_ttl_minutes": {"value": 30},
                    "mfa_enabled": {"value": True},
                },
            },
        }
        await auth_module.save()
        step(f"Created auth_module config: id={auth_module.id}")

        # ==================================================================
        # 4. LIST AND INSPECT CONFIGS
        # ==================================================================

        section("4a. List All Configs")

        configs = await client.config.list()
        for cfg in configs:
            parent_info = f" (parent: {cfg.parent})" if cfg.parent else " (root)"
            step(f"{cfg.key}{parent_info}")

        section("4b. Get a Config by Key")

        fetched = await client.config.get("user_service")
        step(f"Fetched: key={fetched.key}, name={fetched.name}")
        step(f"  description={fetched.description}")
        step(f"  parent={fetched.parent or '(none)'}")
        step(f"  items: {list(fetched.items.keys())}")

        # ==================================================================
        # 5. UPDATE A CONFIG — Active Record
        # ==================================================================

        section("5. Update a Config")

        user_service.description = "User microservice — updated description"
        user_service.environments["production"]["values"]["cache_ttl_seconds"] = {"value": 900}
        await user_service.save()
        step("Updated user_service description and production cache_ttl_seconds")

        # ==================================================================
        # 6. SYNC CLIENT DEMO
        # ==================================================================
        section("6. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplClient
        #
        #     with SmplClient(environment="production", service="my-service") as client:
        #
        #         # Fetch, mutate, save
        #         common = client.config.get("common")
        #         common.items["key"] = {"value": "val", "type": "STRING"}
        #         common.save()
        #
        #         # Create new config
        #         svc = client.config.new("my_svc", name="My Service")
        #         svc.items = {"db.host": {"value": "localhost", "type": "STRING"}}
        #         svc.save()
        #
        #         configs = client.config.list()
        #         client.config.delete("my_svc")

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 7. CLEANUP
        # ==================================================================
        section("7. Cleanup")

        await client.config.delete("auth_module")
        step("Deleted auth_module")

        await client.config.delete("user_service")
        step("Deleted user_service")

        common = await client.config.get("common")
        common.description = ""
        common.items = {}
        common.environments = {}
        await common.save()
        step("Common config reset to empty")

        # ==================================================================
        # DONE
        # ==================================================================
        section("ALL DONE")
        print("  The Config Management showcase completed successfully.")
        print("  All configs have been cleaned up.\n")


if __name__ == "__main__":
    asyncio.run(main())
