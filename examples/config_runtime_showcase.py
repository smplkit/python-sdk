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
        user_svc_config_dict = await client.config.get("showcase-user-service")
        print(f"Total resolved keys: {len(user_svc_config_dict)}")
        print(f"database.host = {user_svc_config_dict.get('database.host')}")
        print(f"max_retries = {user_svc_config_dict.get('max_retries')}")
        print(
            f"cache_ttl_seconds = {user_svc_config_dict.get('cache_ttl_seconds')}"
        )
        print(
            f"pagination_default_page_size = "
            f"{user_svc_config_dict.get('pagination_default_page_size')}"
        )
        print(f"enable_signup = {user_svc_config_dict.get('enable_signup')}")
        print(
            f"nonexistent_key = {user_svc_config_dict.get('nonexistent_key')}"
        )

        # production overrides resolve through the inheritance chain
        assert (
            user_svc_config_dict.get("database.host")
            == "prod-users-rds.internal.acme.dev"
        )
        assert user_svc_config_dict.get("nonexistent_key") is None

        # get a config as a typed model
        user_svc_config = await client.config.get(
            "showcase-user-service", UserServiceConfig
        )
        print(f"cfg.database.host = {user_svc_config.database.host}")
        print(f"cfg.database.pool_size = {user_svc_config.database.pool_size}")
        print(f"cfg.cache_ttl_seconds = {user_svc_config.cache_ttl_seconds}")
        print(f"cfg.enable_signup = {user_svc_config.enable_signup}")
        print(f"cfg.max_retries = {user_svc_config.max_retries}")
        print(f"cfg.app_name = {user_svc_config.app_name}")

        assert isinstance(user_svc_config.database, Database)
        assert user_svc_config.max_retries == 5
        assert user_svc_config.app_name == "Acme SaaS Platform"

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
        common_cfg = await client.config.get("showcase-common")

        @common_cfg.on_change("max_retries")
        def on_retries_change(event):
            retries_changes.append(event)

        # simulate someone making a change to trigger listeners
        await _update_max_retries(client)

        # wait a moment for the event to be delivered
        await asyncio.sleep(0.2)

        # user_svc_config always reflects the latest values
        print(f"max_retries after update = {user_svc_config.max_retries}")
        print(f"Global changes received: {len(changes)}")
        print(f"Retries-specific changes received: {len(retries_changes)}")

        assert user_svc_config.max_retries == 7
        assert len(changes) >= 1
        assert len(retries_changes) >= 1

        await cleanup_runtime_showcase(client.manage)
        print("Done!")


async def _update_max_retries(client: AsyncSmplClient):
    common_cfg = await client.manage.config.get("showcase-common")
    common_cfg.set_number("max_retries", 7, environment="production")
    await common_cfg.save()


if __name__ == "__main__":
    asyncio.run(main())
