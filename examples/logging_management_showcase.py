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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def section(title: str) -> None:
    """Print a section header for readability."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def step(description: str) -> None:
    """Print a step within a section."""
    print(f"  → {description}")


async def main() -> None:

    # ======================================================================
    # 1. SDK INITIALIZATION
    # ======================================================================
    section("1. SDK Initialization")

    # Construct a new management client.  API key may be passed explicitly
    # or via SMPLKIT_API_KEY environment variable.  Alternatively,
    # SMPLKIT_PROFILE environment variable may be specified, in which case the
    # API key will be loaded from the specified profile found in ~/.smplkit.
    async with AsyncSmplManagementClient() as mgmt:
        step("AsyncSmplManagementClient initialized")

        # Clean up leftover loggers and groups from previous runs.
        demo_logger_ids = {"app", "app.payments", "sqlalchemy.engine", "app.internal.debug"}
        demo_group_ids = {"databases", "http_clients"}
        try:
            existing = await mgmt.loggers.list()
            for lg in existing:
                if lg.id in demo_logger_ids:
                    await mgmt.loggers.delete(lg.id)
        except Exception:
            pass
        try:
            existing_groups = await mgmt.log_groups.list()
            for g in existing_groups:
                # Server assigns group IDs from the name (e.g. "HTTP Clients"), normalize for comparison
                normalized = g.id.lower().replace(" ", "_")
                if normalized in demo_group_ids:
                    await mgmt.log_groups.delete(g.id)
        except Exception:
            pass

        # ==================================================================
        # 2. CREATE LOGGERS
        # ==================================================================
        #
        # mgmt.loggers.new(id, *, name=None, managed=False) creates a
        # local Logger instance. Nothing hits the server until save().
        # ==================================================================

        section("2a. Create Managed Loggers")

        app_lg = mgmt.loggers.new("app", name="app", managed=True)
        app_lg.setLevel(LogLevel.WARN)
        await app_lg.save()
        step(f"Created: id={app_lg.id}, managed={app_lg.managed}, level={app_lg.level}")

        payments_lg = mgmt.loggers.new("app.payments", name="app.payments")
        # No level — unmanaged, inherits effective level from dot-notation ancestor "app"
        await payments_lg.save()
        step(f"Created: id={payments_lg.id}, managed={payments_lg.managed}, level={payments_lg.level or '(null)'}")

        sqla_lg = mgmt.loggers.new("sqlalchemy.engine", name="sqlalchemy.engine", managed=True)
        sqla_lg.setLevel(LogLevel.WARN)
        await sqla_lg.save()
        step(f"Created: id={sqla_lg.id}, managed={sqla_lg.managed}, level={sqla_lg.level}")

        section("2b. Create an Unmanaged Logger")

        unmanaged_lg = mgmt.loggers.new("app.internal.debug", name="app.internal.debug", managed=False)
        await unmanaged_lg.save()
        step(f"Created: id={unmanaged_lg.id}, managed={unmanaged_lg.managed}")
        step("  Unmanaged loggers do not consume managed-logger slots")

        # ==================================================================
        # 3. LOGGER INSPECTION
        # ==================================================================

        section("3a. List All Loggers")

        loggers = await mgmt.loggers.list()
        step(f"Total loggers: {len(loggers)}")
        for lg in loggers:
            step(f"  {lg.id} (managed={lg.managed}, level={lg.level or '(null)'})")

        section("3b. Get a Logger by ID")

        fetched = await mgmt.loggers.get("app")
        step(f"Fetched: id={fetched.id}, name={fetched.name}")
        step(f"  managed={fetched.managed}")
        step(f"  level={fetched.level}")
        step(f"  environments={fetched.environments}")

        # ==================================================================
        # 4. LEVEL CONTROL
        # ==================================================================
        #
        # setLevel(LogLevel)               — set base level
        # clearLevel()                     — clear base level (inherit)
        # setEnvironmentLevel(env, level)  — set per-env override
        # clearEnvironmentLevel(env)       — clear per-env override
        # clearAllEnvironmentLevels()      — clear all env overrides
        # ==================================================================

        section("4a. Set Base Level")

        sqla_lg.setLevel(LogLevel.ERROR)
        await sqla_lg.save()
        step(f"Set sqlalchemy.engine base level → {sqla_lg.level}")

        section("4b. Set Environment Overrides")

        app_lg.setEnvironmentLevel("production", LogLevel.ERROR)
        app_lg.setEnvironmentLevel("staging", LogLevel.DEBUG)
        await app_lg.save()
        step(f"Set app environment overrides: {app_lg.environments}")
        step("  production → ERROR, staging → DEBUG, other envs → base (WARN)")

        section("4c. Clear Level — Restore Inheritance")

        sqla_lg.clearLevel()
        await sqla_lg.save()
        step(f"Cleared sqlalchemy.engine level → {sqla_lg.level or '(null)'}")
        step(f"  managed={sqla_lg.managed} — auto-demoted when all configuration is cleared")
        step("  Now inherits from group, dot-notation ancestor, or system default")

        app_lg.clearAllEnvironmentLevels()
        await app_lg.save()
        step(f"Cleared app env overrides → {app_lg.environments}")

        # ==================================================================
        # 5. LOG GROUP CRUD
        # ==================================================================

        section("5a. Create Log Groups")

        db_group = mgmt.log_groups.new("databases", name="Databases")
        db_group.setLevel(LogLevel.ERROR)
        db_group.setEnvironmentLevel("production", LogLevel.WARN)
        await db_group.save()
        step(f"Created group: id={db_group.id}")
        step("  level=ERROR, production override=WARN")

        http_group = mgmt.log_groups.new("http_clients", name="HTTP Clients")
        http_group.setLevel(LogLevel.INFO)
        await http_group.save()
        step(f"Created group: id={http_group.id}")

        section("5b. List Log Groups")

        groups = await mgmt.log_groups.list()
        step(f"Total groups: {len(groups)}")
        for g in groups:
            env_str = f", envs={g.environments}" if g.environments else ""
            step(f"  {g.id}: level={g.level}{env_str}")

        section("5c. Get a Log Group by ID")

        fetched_group = await mgmt.log_groups.get(db_group.id)
        step(f"Fetched: id={fetched_group.id}, name={fetched_group.name}")
        step(f"  level={fetched_group.level}")
        step(f"  environments={fetched_group.environments}")

        section("5d. Update a Log Group")

        http_group.setLevel(LogLevel.DEBUG)
        http_group.setEnvironmentLevel("production", LogLevel.WARN)
        await http_group.save()
        step(f"Updated {http_group.id}: level={http_group.level}, envs={http_group.environments}")

        # ==================================================================
        # 6. GROUP ASSIGNMENT
        # ==================================================================
        section("6. Group Assignment")

        sqla_lg.managed = True  # re-promote before group assignment (auto-demoted in 4c)
        sqla_lg.group = db_group.id
        await sqla_lg.save()
        step(f"Assigned sqlalchemy.engine → group '{db_group.id}'")

        sqla_lg.group = None
        await sqla_lg.save()
        step("Unassigned sqlalchemy.engine from group")

        sqla_lg.group = db_group.id
        await sqla_lg.save()
        step(f"Re-assigned sqlalchemy.engine → group '{db_group.id}'")

        # ==================================================================
        # 7. PROMOTE / RELEASE
        # ==================================================================

        section("7a. Release a Managed Logger")

        step(
            f"Before: id={sqla_lg.id}, managed={sqla_lg.managed}, "
            f"level={sqla_lg.level or '(null)'}, group={sqla_lg.group}"
        )

        sqla_lg.managed = False
        await sqla_lg.save()
        step("Released sqlalchemy.engine → unmanaged")
        step(
            f"After: managed={sqla_lg.managed}, level={sqla_lg.level or '(null)'}, "
            f"group={sqla_lg.group or '(null)'}, environments={sqla_lg.environments}"
        )

        section("7b. Re-Promote a Logger")

        sqla_lg.managed = True
        await sqla_lg.save()
        step(f"Re-promoted: managed={sqla_lg.managed}")
        step("  Starts fresh with level=NULL — admin configures from here")

        # ==================================================================
        # 8. SYNC CLIENT DEMO
        # ==================================================================
        section("8. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplManagementClient, LogLevel
        #
        #     with SmplManagementClient() as mgmt:
        #
        #         # Create a logger
        #         lgr = mgmt.loggers.new("my.logger", managed=True)
        #         lgr.setLevel(LogLevel.WARN)
        #         lgr.save()
        #
        #         # Fetch, mutate, save
        #         lgr = mgmt.loggers.get("my.logger")
        #         lgr.setEnvironmentLevel("production", LogLevel.ERROR)
        #         lgr.save()
        #
        #         # Groups
        #         grp = mgmt.log_groups.new("sql", name="SQL Loggers")
        #         grp.setLevel(LogLevel.WARN)
        #         grp.save()
        #
        #         lgr.group = grp.id
        #         lgr.save()
        #
        #         mgmt.loggers.delete("my.logger")
        #         mgmt.log_groups.delete("sql")

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 8b. REGISTER SYNTHETIC LOGGER SOURCES
        # ==================================================================
        # register() accepts explicit (service, environment) overrides —
        # useful for sample-data seeding, cross-tenant migration, and
        # test fixtures.
        # ==================================================================

        from smplkit.logging import LoggerSource

        section("8b. Register synthetic logger sources")

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
        step("3 sources registered")

        # ==================================================================
        # 9. CLEANUP
        # ==================================================================
        section("9. Cleanup")

        await mgmt.log_groups.delete(db_group.id)
        step(f"Deleted group: {db_group.id}")

        await mgmt.log_groups.delete(http_group.id)
        step(f"Deleted group: {http_group.id}")

        for lg in [app_lg, payments_lg, sqla_lg, unmanaged_lg]:
            await mgmt.loggers.delete(lg.id)
            step(f"Deleted logger: {lg.id}")

        section("ALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
