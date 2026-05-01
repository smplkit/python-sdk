"""Setup / cleanup helpers for ``config_management_showcase.py``."""

from __future__ import annotations

from smplkit import AsyncSmplManagementClient, NotFoundError

_DEMO_ENVIRONMENTS = ["staging", "production"]
_DEMO_CONFIG_IDS = ["showcase-user-service", "showcase-common"]


async def setup_management_showcase(manage: AsyncSmplManagementClient) -> None:
    existing = {env.id for env in await manage.environments.list()}
    for env_id in _DEMO_ENVIRONMENTS:
        if env_id not in existing:
            await manage.environments.new(env_id, name=env_id.title()).save()
    await cleanup_management_showcase(manage)


async def cleanup_management_showcase(manage: AsyncSmplManagementClient) -> None:
    for config_id in _DEMO_CONFIG_IDS:
        try:
            await manage.config.delete(config_id)
        except NotFoundError:
            pass
