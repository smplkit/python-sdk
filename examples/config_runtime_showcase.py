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

from setup.config_runtime_setup import (
    setup_runtime_showcase,
    cleanup_runtime_showcase,
)


class Database(BaseModel):
    host: str
    port: int
    name: str
    pool_size: int


class CommonConfig(BaseModel):
    app_name: str | None = None
    support_email: str | None = None
    max_retries: int = 3
    request_timeout_ms: int = 5000


class UserServiceConfig(CommonConfig):
    database: Database
    cache_ttl_seconds: int
    enable_signup: bool
    pagination_default_page_size: int


async def main() -> None:

    # create the client (use SmplClient for synchronous use)
    async with AsyncSmplClient(
        environment="production", service="showcase-service"
    ) as client:
        await setup_runtime_showcase(client.manage)
        await client.wait_until_ready()

        # get a config as a plain dict
        config_dict = await client.config.get("showcase-user-service")
        print(f"Total resolved keys: {len(config_dict)}")
        print(f"database.host = {config_dict.get('database.host')}")
        print(f"max_retries = {config_dict.get('max_retries')}")
        print(f"cache_ttl_seconds = {config_dict.get('cache_ttl_seconds')}")
        page_size = config_dict.get("pagination_default_page_size")
        print(f"pagination_default_page_size = {page_size}")
        print(f"enable_signup = {config_dict.get('enable_signup')}")
        print(f"nonexistent_key = {config_dict.get('nonexistent_key')}")

        # get a config as a typed model
        cfg = await client.config.get(
            "showcase-user-service", UserServiceConfig
        )
        print(f"cfg.database.host = {cfg.database.host}")
        print(f"cfg.database.pool_size = {cfg.database.pool_size}")
        print(f"cfg.cache_ttl_seconds = {cfg.cache_ttl_seconds}")
        print(f"cfg.enable_signup = {cfg.enable_signup}")
        print(f"cfg.max_retries = {cfg.max_retries}")
        print(f"cfg.app_name = {cfg.app_name}")

        changes: list = []
        retries_changes: list = []

        # global listener — fires when ANY config item changes
        @client.config.on_change
        def on_any_change(event):
            changes.append(event)
            print(
                f"    [CHANGE] {event.config_id}.{event.item_key}: "
                f"{event.old_value!r} -> {event.new_value!r}"
            )

        # item-scoped listener via the live-proxy handle
        shared = await client.config.get("showcase-common")

        @shared.on_change("max_retries")
        def on_retries_change(event):
            retries_changes.append(event)

        # simulate someone making a change to trigger listeners
        shared_mgmt = await client.manage.config.get("showcase-common")
        shared_mgmt.set_number("max_retries", 7, environment="production")
        await shared_mgmt.save()

        # wait a moment for the event to be delivered
        await asyncio.sleep(0.2)

        new_retries = (await client.config.get("showcase-user-service")).get(
            "max_retries"
        )
        print(f"max_retries after update = {new_retries}")
        print(f"Global changes received: {len(changes)}")
        print(f"Retries-specific changes received: {len(retries_changes)}")

        await cleanup_runtime_showcase(client.manage)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
