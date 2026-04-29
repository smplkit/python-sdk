"""
Smpl Config SDK Showcase — Runtime
====================================

Demonstrates the smplkit Python SDK's runtime experience for Smpl Config.

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

from pydantic import BaseModel

from smplkit import AsyncSmplClient

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


# ---------------------------------------------------------------------------
# User-defined models for typed resolution
# ---------------------------------------------------------------------------


class Database(BaseModel):
    host: str
    port: int
    name: str
    pool_size: int


class UserServiceConfig(BaseModel):
    database: Database
    cache_ttl_seconds: int
    enable_signup: bool
    pagination_default_page_size: int
    # Inherited from common:
    app_name: str = ""
    support_email: str = ""
    max_retries: int = 3
    request_timeout_ms: int = 5000


async def main() -> None:

    async with AsyncSmplClient(environment="production", service="showcase-service") as client:
        step("AsyncSmplClient initialized")

        demo = await setup_demo_configs(client.manage)

        # ==================================================================
        # 1. RESOLVE — Plain Dict
        # ==================================================================
        #
        # client.config.get(id) returns a flat dict of resolved values for
        # the current environment.
        # ==================================================================

        section("1. Resolve — Plain Dict")

        config_dict = await client.config.get("user_service")
        step(f"Total resolved keys: {len(config_dict)}")

        step(f"database.host = {config_dict.get('database.host')}")
        # Expected: "prod-users-rds.internal.acme.dev" (production override)

        step(f"max_retries = {config_dict.get('max_retries')}")
        # Expected: 5 (inherited from common's production override)

        step(f"cache_ttl_seconds = {config_dict.get('cache_ttl_seconds')}")
        # Expected: 600 (user_service production override)

        step(f"pagination_default_page_size = {config_dict.get('pagination_default_page_size')}")
        # Expected: 50 (user_service base overrides common's 25)

        step(f"enable_signup = {config_dict.get('enable_signup')}")
        # Expected: False (user_service production override)

        step(f"nonexistent_key = {config_dict.get('nonexistent_key')}")
        # Expected: None

        # ==================================================================
        # 2. RESOLVE — Typed Model
        # ==================================================================
        #
        # Pass a model class to client.config.get() to receive a typed
        # instance instead of a dict.  Dot-notation keys are expanded into
        # nested attributes (``database.host`` → ``cfg.database.host``).
        # ==================================================================

        section("2. Resolve — Typed Model")

        cfg = await client.config.get("user_service", UserServiceConfig)
        step(f"cfg.database.host = {cfg.database.host}")
        step(f"cfg.database.pool_size = {cfg.database.pool_size}")
        step(f"cfg.cache_ttl_seconds = {cfg.cache_ttl_seconds}")
        step(f"cfg.enable_signup = {cfg.enable_signup}")
        step(f"cfg.max_retries = {cfg.max_retries}")
        step(f"cfg.app_name = {cfg.app_name}")

        assert isinstance(cfg, UserServiceConfig)
        assert isinstance(cfg.database, Database)

        # ==================================================================
        # 3. INHERITANCE
        # ==================================================================
        #
        # auth_module inherits from common. Values defined in auth_module
        # take precedence; anything not overridden falls through to common.
        # ==================================================================

        section("3. Inheritance (auth_module)")

        auth_dict = await client.config.get("auth_module")
        step(f"session_ttl_minutes = {auth_dict.get('session_ttl_minutes')}")
        # Expected: 30 (auth_module production override)

        step(f"mfa_enabled = {auth_dict.get('mfa_enabled')}")
        # Expected: True (auth_module production override)

        step(f"app_name (inherited from common) = {auth_dict.get('app_name')}")
        # Expected: "Acme SaaS Platform"

        # ==================================================================
        # 4. SUBSCRIBE — Live Proxy
        # ==================================================================
        #
        # client.config.subscribe() returns a live proxy that auto-updates
        # when config values change on the server.
        # ==================================================================

        section("4. Subscribe — Live Proxy")

        live = await client.config.subscribe("user_service", UserServiceConfig)
        step(f"live.database.host = {live.database.host}")
        step(f"live.cache_ttl_seconds = {live.cache_ttl_seconds}")

        # ==================================================================
        # 5. CHANGE LISTENERS
        # ==================================================================
        #
        # Register a listener with @client.config.on_change.  Three forms:
        #
        #   @client.config.on_change                       — any change
        #   @client.config.on_change("user_service")       — config-scoped
        #   @client.config.on_change("user_service", item_key="database.host")
        #                                                  — item-scoped
        # ==================================================================

        section("5a. Change Listeners")

        changes: list = []

        @client.config.on_change
        def on_any_change(event):
            changes.append(event)
            print(f"    [CHANGE] {event.config_id}.{event.item_key}: {event.old_value!r} -> {event.new_value!r}")

        step("Global change listener registered")

        retries_changes: list = []

        @client.config.on_change("common", item_key="max_retries")
        def on_retries_change(event):
            retries_changes.append(event)

        step("Item-specific listener registered for common.max_retries")

        # ------------------------------------------------------------------
        # 5b. Simulate a change
        # ------------------------------------------------------------------
        section("5b. Simulate a Change")

        common = await client.manage.configs.get("common")
        common.environments["production"]["values"]["max_retries"] = {"value": 7}
        await common.save()
        step("Updated max_retries to 7 on common (production)")

        await asyncio.sleep(2)

        # Read the updated value — should reflect the change.
        new_retries = (await client.config.get("user_service")).get("max_retries")
        step(f"max_retries after update = {new_retries}")
        # Expected: 7

        step(f"Global changes received: {len(changes)}")
        step(f"Retries-specific changes received: {len(retries_changes)}")

        # ==================================================================
        # 6. SYNC CLIENT DEMO
        # ==================================================================
        section("6. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplClient
        #
        #     with SmplClient(environment="production", service="my-service") as client:
        #         config = client.config.get("user_service")
        #         host = config["database.host"]
        #
        #         cfg = client.config.get("user_service", UserServiceConfig)
        #         print(cfg.database.host)
        #
        #         live = client.config.subscribe("user_service", UserServiceConfig)
        #         print(live.database.host)

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 7. CLEANUP
        # ==================================================================
        section("7. Cleanup")

        await teardown_demo_configs(client.manage, demo)

        section("ALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
