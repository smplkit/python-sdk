"""Setup / cleanup helpers for ``flags_management_showcase.py``."""

from __future__ import annotations

from smplkit import AsyncSmplManagementClient, NotFoundError

_DEMO_ENVIRONMENTS = ["staging", "production"]
_DEMO_FLAG_IDS = ["checkout-v2", "banner-color", "max-retries", "ui-theme"]


async def setup_management_showcase(manage: AsyncSmplManagementClient) -> None:
    existing = {env.id for env in await manage.environments.list()}
    for env_id in _DEMO_ENVIRONMENTS:
        if env_id not in existing:
            await manage.environments.new(env_id, name=env_id.title()).save()
    await cleanup_management_showcase(manage)


async def cleanup_management_showcase(manage: AsyncSmplManagementClient) -> None:
    for flag_id in _DEMO_FLAG_IDS:
        try:
            await manage.flags.delete(flag_id)
        except NotFoundError:
            pass
