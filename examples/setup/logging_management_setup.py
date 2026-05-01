"""Setup / cleanup helpers for ``logging_management_showcase.py``."""

from __future__ import annotations

from smplkit import AsyncSmplManagementClient, NotFoundError

_DEMO_LOGGER_IDS = ["app", "app.payments", "sqlalchemy.engine", "app.internal.debug", "httpx"]
_DEMO_GROUP_IDS = ["databases", "http_clients"]


async def setup_management_showcase(manage: AsyncSmplManagementClient) -> None:
    await cleanup_management_showcase(manage)


async def cleanup_management_showcase(manage: AsyncSmplManagementClient) -> None:
    for logger_id in _DEMO_LOGGER_IDS:
        try:
            await manage.loggers.delete(logger_id)
        except NotFoundError:
            pass
    for group_id in _DEMO_GROUP_IDS:
        try:
            await manage.log_groups.delete(group_id)
        except NotFoundError:
            pass
