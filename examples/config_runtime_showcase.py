"""
Smpl Config SDK Showcase — Runtime
====================================

Demonstrates the smplkit Python SDK's runtime experience for Smpl Config:

- Lazy initialization — first resolve() fetches configs and opens WebSocket
- resolve(id) → plain dict of resolved values
- resolve(id, Model) → typed Pydantic model
- subscribe() → live proxy that updates automatically
- Config inheritance (common → service / module)
- Environment-specific override resolution
- @client.config.on_change decorator with optional id/item scoping

This is the SDK experience that 99%% of customers will use. Configs are
created and maintained via the Console UI (or the management API shown
in ``config_management_showcase.py``). This script focuses entirely on
the runtime: resolving values, subscribing for updates, and reacting
to changes.

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
        step("AsyncSmplClient initialized (environment=production, service=showcase-service)")

        # Create server-side state (normally done via Console UI).
        print("  Setting up demo configs...")
        demo = await setup_demo_configs(client)
        print("  Demo configs ready.\n")

        # The server now has:
        #   "common"       — org-wide defaults, with production + staging overrides
        #   "user_service" — service config (inherits from common), with production overrides
        #   "auth_module"  — auth config (inherits from common), with production overrides

        # ==================================================================
        # 2. RESOLVE — Plain Dict
        # ==================================================================
        #
        # resolve(id) returns a flat dict of resolved values for the
        # current environment. Inheritance is walked, environment overrides
        # applied, values unwrapped from their typed definitions.
        #
        # The FIRST resolve() call triggers lazy initialization:
        #   1. Bulk-fetches all configs
        #   2. Resolves inheritance and environment overrides
        #   3. Opens the shared WebSocket for live updates
        #
        # Subsequent calls are pure local cache reads — no network.
        # ==================================================================

        section("2. Resolve — Plain Dict")

        config_dict = await client.config.resolve("user_service")
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
        # 3. RESOLVE — Typed Model
        # ==================================================================
        #
        # resolve(id, Model) builds a nested dict from flat dot-notation
        # keys and constructs the model from it:
        #   "database.host" + "database.port" → {"database": {"host": ..., "port": ...}}
        #   → UserServiceConfig(database=Database(host=..., port=...))
        #
        # Works with Pydantic models (which handle nested coercion
        # automatically via model_validate) or any class whose
        # constructor accepts keyword arguments.
        # ==================================================================

        section("3. Resolve — Typed Model")

        cfg = await client.config.resolve("user_service", UserServiceConfig)
        step(f"cfg.database.host = {cfg.database.host}")
        step(f"cfg.database.pool_size = {cfg.database.pool_size}")
        step(f"cfg.cache_ttl_seconds = {cfg.cache_ttl_seconds}")
        step(f"cfg.enable_signup = {cfg.enable_signup}")
        step(f"cfg.max_retries = {cfg.max_retries}")
        step(f"cfg.app_name = {cfg.app_name}")

        assert isinstance(cfg, UserServiceConfig)
        assert isinstance(cfg.database, Database)
        step("Type assertions passed ✓")

        # ==================================================================
        # 4. INHERITANCE
        # ==================================================================
        #
        # auth_module inherits from common. Values defined in auth_module
        # take precedence; anything not overridden falls through to common.
        # ==================================================================

        section("4. Inheritance (auth_module)")

        auth_dict = await client.config.resolve("auth_module")
        step(f"session_ttl_minutes = {auth_dict.get('session_ttl_minutes')}")
        # Expected: 30 (auth_module production override)

        step(f"mfa_enabled = {auth_dict.get('mfa_enabled')}")
        # Expected: True (auth_module production override)

        step(f"app_name (inherited from common) = {auth_dict.get('app_name')}")
        # Expected: "Acme SaaS Platform"

        # ==================================================================
        # 5. SUBSCRIBE — Live Proxy
        # ==================================================================
        #
        # subscribe() returns a live proxy that always reflects the latest
        # server-side state without re-fetching. When a WebSocket event
        # arrives, the proxy's underlying data is updated automatically.
        # ==================================================================

        section("5. Subscribe — Live Proxy")

        live = await client.config.subscribe("user_service", UserServiceConfig)
        step(f"live.database.host = {live.database.host}")
        step(f"live.cache_ttl_seconds = {live.cache_ttl_seconds}")
        step("This proxy will reflect new values after server-side changes")
        step("propagate via WebSocket — no polling, no re-fetch needed.")

        # ==================================================================
        # 6. CHANGE LISTENERS
        # ==================================================================
        #
        # @client.config.on_change — fires when ANY config changes
        # @client.config.on_change("user-service") — scoped to a config id
        # @client.config.on_change("user-service", item_key="database.host")
        #     — scoped to a specific item
        # ==================================================================

        section("6a. Change Listeners")

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
        # 6b. Trigger a change via management API, then let WebSocket deliver
        # ------------------------------------------------------------------
        section("6b. Trigger a Change")

        common = await client.config.get("common")
        common.environments["production"]["values"]["max_retries"] = {"value": 7}
        await common.save()
        step("Updated max_retries to 7 on common (production) via management API")

        # Give WebSocket a moment to deliver the update.
        await asyncio.sleep(2)

        # Read the updated value — should reflect the change.
        new_retries = (await client.config.resolve("user_service")).get("max_retries")
        step(f"max_retries after WebSocket update = {new_retries}")
        # Expected: 7

        step(f"Global changes received: {len(changes)}")
        step(f"Retries-specific changes received: {len(retries_changes)}")

        # ==================================================================
        # 7. SYNC CLIENT DEMO
        # ==================================================================
        section("7. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplClient
        #
        #     with SmplClient(environment="production", service="my-service") as client:
        #
        #         # First resolve() triggers lazy init
        #         config = client.config.resolve("user_service")
        #         host = config["database.host"]
        #
        #         # Typed resolution
        #         cfg = client.config.resolve("user_service", UserServiceConfig)
        #         print(cfg.database.host)
        #
        #         # Live proxy
        #         live = client.config.subscribe("user_service", UserServiceConfig)
        #         print(live.database.host)  # always current

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 8. CLEANUP
        # ==================================================================
        section("8. Cleanup")

        await teardown_demo_configs(client, demo)
        step("Demo configs deleted")

        # ==================================================================
        # DONE
        # ==================================================================
        section("ALL DONE")
        print("  The Config Runtime showcase completed successfully.")
        print("  If you got here, Smpl Config is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
