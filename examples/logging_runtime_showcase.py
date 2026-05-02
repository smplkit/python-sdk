"""
Smpl Logging SDK Showcase — Runtime
=====================================

Demonstrates the smplkit Python SDK's runtime experience for Smpl Logging.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The smplkit Logging service running and reachable

Usage::

    python examples/logging_runtime_showcase.py
"""

import asyncio
import logging as stdlib_logging

from smplkit import AsyncSmplClient, LogLevel

from setup.logging_runtime_setup import (
    setup_runtime_showcase,
    cleanup_runtime_showcase,
)


def python_level_name(logger_name: str) -> str:
    """Return the current Python logging level name for a logger."""
    lvl = stdlib_logging.getLogger(logger_name).getEffectiveLevel()
    return stdlib_logging.getLevelName(lvl)


async def main() -> None:

    # application loggers — what your code uses
    stdlib_logging.getLogger("app").setLevel(stdlib_logging.INFO)
    stdlib_logging.getLogger("app.payments").setLevel(stdlib_logging.WARNING)
    stdlib_logging.getLogger("sqlalchemy.engine").setLevel(
        stdlib_logging.WARNING
    )

    ENVIRONMENT = "production"

    # create the client (use SmplClient for synchronous use)
    async with AsyncSmplClient(
        environment=ENVIRONMENT, service="showcase-service"
    ) as client:
        await setup_runtime_showcase(client.manage, environment=ENVIRONMENT)

        all_changes: list = []

        # global listener — fires when ANY logger or group changes
        @client.logging.on_change
        def on_any_change(event):
            all_changes.append(event)
            print(f"    [CHANGE] {event.id} changed")

        sql_changes: list = []

        # scoped listener — fires only for sqlalchemy.engine
        @client.logging.on_change("sqlalchemy.engine")
        def on_sql_change(event):
            sql_changes.append(event)
            print("    [SQL] sqlalchemy.engine changed")

        # python levels before start() — application defaults
        for name in ["app", "app.payments", "sqlalchemy.engine"]:
            print(f"  {name}: {python_level_name(name)}")

        # opt in to runtime level management
        await client.logging.start()
        print("client.logging.start() completed")

        # python levels after start() — smplkit has taken control
        for name in ["app", "app.payments", "sqlalchemy.engine"]:
            print(f"  {name}: {python_level_name(name)}")

        # smplkit pushed the production override down to stdlib
        assert python_level_name("app") == "ERROR"

        # level resolution — first non-null wins:
        #   1. Logger's own environment override
        #   2. Logger's own base level
        #   3. Group chain (recursive up the group hierarchy)
        #   4. Dot-notation ancestry (walk "app.payments" → "app")
        #   5. System fallback: INFO
        print(f"  app → {python_level_name('app')}")
        print(f"  app.payments → {python_level_name('app.payments')}")
        print(
            f"  sqlalchemy.engine → {python_level_name('sqlalchemy.engine')}"
        )

        # change a group level — all members shift
        db_group = await client.manage.log_groups.get("databases")
        before = python_level_name("sqlalchemy.engine")
        print(f"sqlalchemy.engine before: {before}")

        db_group.set_level(LogLevel.DEBUG, environment=ENVIRONMENT)
        await db_group.save()
        print(f"Changed databases group {ENVIRONMENT} override: WARN -> DEBUG")

        await asyncio.sleep(2)

        after = python_level_name("sqlalchemy.engine")
        print(f"sqlalchemy.engine after: {after}")

        # change an ancestor level — dot-notation children shift
        app_lg = await client.manage.loggers.get("app")
        print(f"app.payments before: {python_level_name('app.payments')}")

        app_lg.set_level(LogLevel.TRACE, environment=ENVIRONMENT)
        await app_lg.save()
        print(f"Changed app {ENVIRONMENT} override: ERROR → TRACE")

        await asyncio.sleep(2)

        print(f"app after: {python_level_name('app')}")
        print(f"app.payments after: {python_level_name('app.payments')}")

        # TRACE (level 5) propagated through smplkit → stdlib
        assert python_level_name("app") == "Level 5"

        # clear an environment override — falls through to base level
        print(f"app before: {python_level_name('app')}")

        app_lg.clear_all_environment_levels()
        await app_lg.save()

        await asyncio.sleep(2)

        print(f"app after: {python_level_name('app')}")
        print(f"app.payments after: {python_level_name('app.payments')}")

        # production override gone — fell through to base WARN
        assert python_level_name("app") == "WARNING"

        # continuous discovery — new loggers after start() are picked up
        new_logger = stdlib_logging.getLogger("app.notifications")
        new_logger.setLevel(stdlib_logging.INFO)
        print("Created: app.notifications (INFO)")

        print(f"Global changes received: {len(all_changes)}")
        print(f"SQL-specific changes received: {len(sql_changes)}")

        assert len(all_changes) >= 1

        await cleanup_runtime_showcase(client.manage)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
