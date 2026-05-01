"""Setup / cleanup helpers for ``logging_runtime_showcase.py``."""

from __future__ import annotations

from smplkit import AsyncSmplManagementClient, LogLevel, NotFoundError

_DEMO_LOGGER_IDS = [
    "app",
    "app.payments",
    "sqlalchemy.engine",
    "app.notifications",
]
_DEMO_GROUP_IDS = ["databases"]


async def setup_runtime_showcase(
    manage: AsyncSmplManagementClient, environment: str
) -> None:
    await cleanup_runtime_showcase(manage)

    db_group = manage.log_groups.new("databases", name="Databases")
    db_group.set_level(LogLevel.ERROR)
    db_group.set_level(LogLevel.WARN, environment=environment)
    await db_group.save()

    app_lg = manage.loggers.new("app", name="app", managed=True)
    app_lg.set_level(LogLevel.WARN)
    app_lg.set_level(LogLevel.ERROR, environment=environment)
    await app_lg.save()

    payments_lg = manage.loggers.new(
        "app.payments", name="app.payments", managed=True
    )
    await payments_lg.save()

    sqla_lg = manage.loggers.new(
        "sqlalchemy.engine", name="sqlalchemy.engine", managed=True
    )
    sqla_lg.group = db_group.id
    await sqla_lg.save()


async def cleanup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
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
