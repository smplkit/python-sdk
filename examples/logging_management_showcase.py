"""
Smpl Logging SDK Showcase — Management API
============================================

Demonstrates the smplkit Python SDK's management plane for Smpl Logging.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - The smplkit Logging service running and reachable

Usage::

    python examples/logging_management_showcase.py
"""

import asyncio

from smplkit import AsyncSmplManagementClient, LogLevel

from setup.logging_management_setup import cleanup_management_showcase, setup_management_showcase


async def main() -> None:

    # create the client (use SmplManagementClient for synchronous use)
    async with AsyncSmplManagementClient() as mgmt:
        await setup_management_showcase(mgmt)

        # create a managed logger
        app_lg = mgmt.loggers.new("app", name="app", managed=True)
        app_lg.set_level(LogLevel.WARN)
        await app_lg.save()
        print(f"Created: id={app_lg.id}, managed={app_lg.managed}, level={app_lg.level}")

        # unmanaged — inherits effective level from dot-notation ancestor "app"
        payments_lg = mgmt.loggers.new("app.payments", name="app.payments")
        await payments_lg.save()
        print(f"Created: id={payments_lg.id}, managed={payments_lg.managed}, level={payments_lg.level or '(null)'}")

        sqla_lg = mgmt.loggers.new("sqlalchemy.engine", name="sqlalchemy.engine", managed=True)
        sqla_lg.set_level(LogLevel.WARN)
        await sqla_lg.save()
        print(f"Created: id={sqla_lg.id}, managed={sqla_lg.managed}, level={sqla_lg.level}")

        # unmanaged loggers do not consume managed-logger slots
        unmanaged_lg = mgmt.loggers.new("app.internal.debug", name="app.internal.debug", managed=False)
        await unmanaged_lg.save()
        print(f"Created: id={unmanaged_lg.id}, managed={unmanaged_lg.managed}")

        # list all loggers
        loggers = await mgmt.loggers.list()
        print(f"Total loggers: {len(loggers)}")
        for lg in loggers:
            print(f"  {lg.id} (managed={lg.managed}, level={lg.level or '(null)'})")

        # get a logger by id
        fetched = await mgmt.loggers.get("app")
        print(f"Fetched: id={fetched.id}, name={fetched.name}")
        print(f"  managed={fetched.managed}")
        print(f"  level={fetched.level}")
        print(f"  environments={fetched.environments}")

        # set base level
        sqla_lg.set_level(LogLevel.ERROR)
        await sqla_lg.save()
        print(f"Set sqlalchemy.engine base level → {sqla_lg.level}")

        # set per-environment overrides
        app_lg.set_level(LogLevel.ERROR, environment="production")
        app_lg.set_level(LogLevel.DEBUG, environment="staging")
        await app_lg.save()
        print(f"Set app environment overrides: {app_lg.environments}")

        # clear level — restore inheritance (auto-demoted when all configuration is cleared)
        sqla_lg.clear_level()
        await sqla_lg.save()
        print(f"Cleared sqlalchemy.engine level → {sqla_lg.level or '(null)'}, managed={sqla_lg.managed}")

        app_lg.clear_all_environment_levels()
        await app_lg.save()
        print(f"Cleared app env overrides → {app_lg.environments}")

        # create log groups
        db_group = mgmt.log_groups.new("databases", name="Databases")
        db_group.set_level(LogLevel.ERROR)
        db_group.set_level(LogLevel.WARN, environment="production")
        await db_group.save()
        print(f"Created group: {db_group.id}")

        http_group = mgmt.log_groups.new("http_clients", name="HTTP Clients")
        http_group.set_level(LogLevel.INFO)
        await http_group.save()
        print(f"Created group: {http_group.id}")

        # list log groups
        groups = await mgmt.log_groups.list()
        print(f"Total groups: {len(groups)}")
        for g in groups:
            env_str = f", envs={g.environments}" if g.environments else ""
            print(f"  {g.id}: level={g.level}{env_str}")

        # get a log group by id
        fetched_group = await mgmt.log_groups.get(db_group.id)
        print(f"Fetched: id={fetched_group.id}, name={fetched_group.name}")
        print(f"  level={fetched_group.level}")
        print(f"  environments={fetched_group.environments}")

        # update a log group
        http_group.set_level(LogLevel.DEBUG)
        http_group.set_level(LogLevel.WARN, environment="production")
        await http_group.save()
        print(f"Updated {http_group.id}: level={http_group.level}, envs={http_group.environments}")

        # group assignment
        sqla_lg.managed = True  # re-promote before group assignment (auto-demoted above)
        sqla_lg.group = db_group.id
        await sqla_lg.save()
        print(f"Assigned sqlalchemy.engine → group '{db_group.id}'")

        sqla_lg.group = None
        await sqla_lg.save()
        print("Unassigned sqlalchemy.engine from group")

        sqla_lg.group = db_group.id
        await sqla_lg.save()
        print(f"Re-assigned sqlalchemy.engine → group '{db_group.id}'")

        # release a managed logger
        print(
            f"Before release: id={sqla_lg.id}, managed={sqla_lg.managed}, "
            f"level={sqla_lg.level or '(null)'}, group={sqla_lg.group}"
        )
        sqla_lg.managed = False
        await sqla_lg.save()
        print(
            f"After release: managed={sqla_lg.managed}, level={sqla_lg.level or '(null)'}, "
            f"group={sqla_lg.group or '(null)'}, environments={sqla_lg.environments}"
        )

        # re-promote — starts fresh with level=NULL
        sqla_lg.managed = True
        await sqla_lg.save()
        print(f"Re-promoted: managed={sqla_lg.managed}")

        # register synthetic logger sources — useful for sample-data seeding,
        # cross-tenant migration, and test fixtures
        from smplkit.logging import LoggerSource

        mgmt.loggers.register(
            [
                LoggerSource(
                    "sqlalchemy.engine",
                    service="user-service",
                    environment="production",
                    resolved_level=LogLevel.WARN,
                ),
                LoggerSource(
                    "sqlalchemy.engine",
                    service="payment-service",
                    environment="production",
                    resolved_level=LogLevel.WARN,
                ),
                LoggerSource(
                    "httpx",
                    service="checkout-service",
                    environment="staging",
                    resolved_level=LogLevel.INFO,
                ),
            ]
        )
        await mgmt.loggers.flush()
        print("3 sources registered")

        # delete groups and loggers (by ID or directly)
        await mgmt.log_groups.delete(db_group.id)
        await mgmt.log_groups.delete(http_group.id)
        for lg in [app_lg, payments_lg, sqla_lg, unmanaged_lg]:
            await mgmt.loggers.delete(lg.id)
        print("Deleted groups and loggers")

        # cleanup
        await cleanup_management_showcase(mgmt)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
