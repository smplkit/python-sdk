"""
Demonstrates the smplkit runtime SDK for Smpl Config.

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

from setup.config_runtime_setup import setup_runtime_showcase, cleanup_runtime_showcase


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
    # Inherited from showcase-common:
    app_name: str = ""
    support_email: str = ""
    max_retries: int = 3
    request_timeout_ms: int = 5000


async def main() -> None:

    # create the client (use SmplClient for synchronous use)
    async with AsyncSmplClient(environment="production", service="showcase-service") as client:
        await setup_runtime_showcase(client.manage)
        await client.wait_until_ready()

        # resolve as plain dict
        config_dict = await client.config.get("showcase-user-service")
        print(f"Total resolved keys: {len(config_dict)}")
        print(f"database.host = {config_dict.get('database.host')}")
        print(f"max_retries = {config_dict.get('max_retries')}")
        print(f"cache_ttl_seconds = {config_dict.get('cache_ttl_seconds')}")
        print(f"pagination_default_page_size = {config_dict.get('pagination_default_page_size')}")
        print(f"enable_signup = {config_dict.get('enable_signup')}")
        print(f"nonexistent_key = {config_dict.get('nonexistent_key')}")

        # resolve as a typed model — dot-notation keys expand into nested attributes
        cfg = await client.config.get("showcase-user-service", UserServiceConfig)
        print(f"cfg.database.host = {cfg.database.host}")
        print(f"cfg.database.pool_size = {cfg.database.pool_size}")
        print(f"cfg.cache_ttl_seconds = {cfg.cache_ttl_seconds}")
        print(f"cfg.enable_signup = {cfg.enable_signup}")
        print(f"cfg.max_retries = {cfg.max_retries}")
        print(f"cfg.app_name = {cfg.app_name}")

        assert isinstance(cfg, UserServiceConfig)
        assert isinstance(cfg.database, Database)

        # showcase-auth-module inherits from showcase-common
        auth_dict = await client.config.get("showcase-auth-module")
        print(f"session_ttl_minutes = {auth_dict.get('session_ttl_minutes')}")
        print(f"mfa_enabled = {auth_dict.get('mfa_enabled')}")
        print(f"app_name (inherited from showcase-common) = {auth_dict.get('app_name')}")

        # subscribe — live proxy that auto-updates when values change on the server
        live = await client.config.subscribe("showcase-user-service", UserServiceConfig)
        print(f"live.database.host = {live.database.host}")
        print(f"live.cache_ttl_seconds = {live.cache_ttl_seconds}")

        changes: list = []

        # global listener — fires when ANY config item changes
        @client.config.on_change
        def on_any_change(event):
            changes.append(event)
            print(f"    [CHANGE] {event.config_id}.{event.item_key}: {event.old_value!r} -> {event.new_value!r}")

        retries_changes: list = []

        # item-scoped listener — fires only when showcase-common.max_retries changes
        @client.config.on_change("showcase-common", item_key="max_retries")
        def on_retries_change(event):
            retries_changes.append(event)

        # simulate someone making a change to trigger listeners
        shared = await client.manage.config.get("showcase-common")
        shared.set_number("max_retries", 7, environment="production")
        await shared.save()

        await asyncio.sleep(2)

        new_retries = (await client.config.get("showcase-user-service")).get("max_retries")
        print(f"max_retries after update = {new_retries}")

        print(f"Global changes received: {len(changes)}")
        print(f"Retries-specific changes received: {len(retries_changes)}")

        await cleanup_runtime_showcase(client.manage)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
