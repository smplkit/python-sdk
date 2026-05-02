"""
Demonstrates the smplkit management SDK for Smpl Logging.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/logging_management_showcase.py
"""

import asyncio

from smplkit import AsyncSmplManagementClient, LogLevel

from setup.logging_management_setup import (
    cleanup_management_showcase,
    setup_management_showcase,
)


async def main() -> None:

    # create the client (use SmplManagementClient for synchronous use)
    async with AsyncSmplManagementClient() as manage:
        await setup_management_showcase(manage)

        # create a parent logger with a default level
        root = manage.loggers.new("showcase")
        root.set_level(LogLevel.INFO)
        await root.save()
        print(f"Created: {root.id} (level={root.level})")
        assert root.level == LogLevel.INFO

        # child logger with no level (inherits from parent)
        db = manage.loggers.new("showcase.db")
        await db.save()
        print(f"Created: {db.id} (inherits)")
        assert db.level is None

        # child logger with explicit level (overrides parent)
        payments = manage.loggers.new("showcase.payments")
        payments.set_level(LogLevel.WARN)
        await payments.save()
        print(f"Created: {payments.id} (level={payments.level})")
        assert payments.level == LogLevel.WARN

        # override log level for different environments
        root.set_level(LogLevel.ERROR, environment="production")
        root.set_level(LogLevel.DEBUG, environment="staging")
        await root.save()
        print(f"Set environment overrides: {root.environments}")
        assert root.environments["production"].level == LogLevel.ERROR
        assert root.environments["staging"].level == LogLevel.DEBUG

        # clear environment override (inherits from the default level again)
        root.clear_level(environment="staging")
        await root.save()
        print(f"Cleared staging override: {root.environments}")
        assert "staging" not in root.environments
        assert root.environments["production"].level == LogLevel.ERROR

        # fetch a logger by id
        fetched = await manage.loggers.get("showcase")
        assert fetched.level == LogLevel.INFO

        await cleanup_management_showcase(manage)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
