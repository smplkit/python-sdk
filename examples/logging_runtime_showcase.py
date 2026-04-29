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

from logging_runtime_setup import setup_demo_loggers, teardown_demo_loggers

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


def python_level_name(logger_name: str) -> str:
    """Return the current Python logging level name for a logger."""
    lvl = stdlib_logging.getLogger(logger_name).getEffectiveLevel()
    return stdlib_logging.getLevelName(lvl)


async def main() -> None:

    # Application loggers — what your code uses.
    stdlib_logging.getLogger("app").setLevel(stdlib_logging.INFO)
    stdlib_logging.getLogger("app.payments").setLevel(stdlib_logging.WARNING)
    stdlib_logging.getLogger("sqlalchemy.engine").setLevel(stdlib_logging.WARNING)

    section("SDK Initialization")

    ENVIRONMENT = "production"

    async with AsyncSmplClient(environment=ENVIRONMENT, service="showcase-service") as client:
        step("AsyncSmplClient initialized")

        demo = await setup_demo_loggers(client.manage, environment=ENVIRONMENT)

        # ==================================================================
        # 1. CHANGE LISTENERS
        # ==================================================================
        #
        # Register listeners with @client.logging.on_change.  Two forms:
        #
        #   @client.logging.on_change                       — any change
        #   @client.logging.on_change("sqlalchemy.engine")  — id-scoped
        #
        # Listeners can be registered before start().
        # ==================================================================

        section("1. Register Change Listeners")

        all_changes: list = []

        @client.logging.on_change
        def on_any_change(event):
            all_changes.append(event)
            print(f"    [CHANGE] {event.id} changed")

        step("Global change listener registered")

        sql_changes: list = []

        @client.logging.on_change("sqlalchemy.engine")
        def on_sql_change(event):
            sql_changes.append(event)
            print("    [SQL] sqlalchemy.engine changed")

        step("Scoped listener registered for sqlalchemy.engine")

        # ==================================================================
        # 2. START
        # ==================================================================
        #
        # client.logging.start() opts in to runtime level management.
        # It picks up the loggers your code has already created and applies
        # the levels you've configured on the server.  Idempotent.
        # ==================================================================

        section("2. Auto-Discovery + Start")

        step("Python levels before start() (application defaults):")
        for name in ["app", "app.payments", "sqlalchemy.engine"]:
            step(f"  {name}: {python_level_name(name)}")
        # Expected: INFO, WARNING, WARNING

        await client.logging.start()
        step("\nclient.logging.start() completed")

        step("\nPython levels after start() (smplkit has taken control):")
        for name in ["app", "app.payments", "sqlalchemy.engine"]:
            step(f"  {name}: {python_level_name(name)}")
        # Expected: ERROR, ERROR, WARNING — resolved per the chain below

        # ==================================================================
        # 3. LEVEL RESOLUTION
        # ==================================================================
        #
        # Resolution chain (first non-null wins):
        #   1. Logger's own environment override
        #   2. Logger's own base level
        #   3. Group chain (recursive up the group hierarchy)
        #   4. Dot-notation ancestry (walk "app.payments" → "app")
        #   5. System fallback: INFO
        # ==================================================================

        section("3. Level Resolution")

        step(f"  app → {python_level_name('app')}")
        step(f"    Resolution: env override ({ENVIRONMENT}=ERROR) ✓")

        step(f"\n  app.payments → {python_level_name('app.payments')}")
        step("    Resolution: no level → no group → ancestor 'app' → ERROR ✓")

        step(f"\n  sqlalchemy.engine → {python_level_name('sqlalchemy.engine')}")
        step(f"    Resolution: no level → group 'databases' → env override ({ENVIRONMENT}=WARN) ✓")

        # ==================================================================
        # 4. DYNAMIC LEVEL CONTROL
        # ==================================================================
        #
        # Change a level on the server.  The runtime client picks up the
        # change automatically and re-applies the resolution chain.
        # ==================================================================

        # ------------------------------------------------------------------
        # 4a. Change a group level — all members shift
        # ------------------------------------------------------------------
        section("4a. Change Group Level")

        db_group = await client.manage.log_groups.get(demo["group_ids"][0])
        step(f"sqlalchemy.engine before: {python_level_name('sqlalchemy.engine')}")

        db_group.setEnvironmentLevel(ENVIRONMENT, LogLevel.DEBUG)
        await db_group.save()
        step(f"Changed databases group {ENVIRONMENT} override: WARN → DEBUG")

        await asyncio.sleep(2)

        step(f"sqlalchemy.engine after: {python_level_name('sqlalchemy.engine')}")
        step("  Group-level change cascaded to all group members")

        # ------------------------------------------------------------------
        # 4b. Change an ancestor level — dot-notation children shift
        # ------------------------------------------------------------------
        section("4b. Change Ancestor Level")

        app_lg = await client.manage.loggers.get("app")
        step(f"app.payments before: {python_level_name('app.payments')}")

        app_lg.setEnvironmentLevel(ENVIRONMENT, LogLevel.TRACE)
        await app_lg.save()
        step(f"Changed app {ENVIRONMENT} override: ERROR → TRACE")

        await asyncio.sleep(2)

        step(f"app after: {python_level_name('app')}")
        step(f"app.payments after: {python_level_name('app.payments')}")
        step("  Ancestor-level change cascaded via dot-notation hierarchy")

        # ------------------------------------------------------------------
        # 4c. Clear an environment override — falls through to base level
        # ------------------------------------------------------------------
        section("4c. Clear Override")

        step(f"app before: {python_level_name('app')}")

        app_lg.clearAllEnvironmentLevels()
        await app_lg.save()
        step("Cleared all env overrides on app")

        await asyncio.sleep(2)

        step(f"app after: {python_level_name('app')}")
        # Expected: WARNING — no env override, falls through to base level (WARN)

        step(f"app.payments after: {python_level_name('app.payments')}")
        # Expected: WARNING — inherits from ancestor "app"

        # ==================================================================
        # 5. CONTINUOUS DISCOVERY
        # ==================================================================
        #
        # New Python loggers created after start() are picked up
        # automatically — no extra wiring needed.
        # ==================================================================

        section("5. Continuous Discovery")

        step("Creating a new Python logger after start()...")
        new_logger = stdlib_logging.getLogger("app.notifications")
        new_logger.setLevel(stdlib_logging.INFO)
        step("Created: app.notifications (INFO)")

        # ==================================================================
        # 6. CHANGE LISTENER RESULTS
        # ==================================================================
        section("6. Change Listener Results")

        step(f"Global changes received: {len(all_changes)}")
        step(f"SQL-specific changes received: {len(sql_changes)}")

        # ==================================================================
        # 7. SYNC CLIENT DEMO
        # ==================================================================
        section("7. Sync Client (same API, no await)")

        # For sync applications (Django, Flask, CLI tools):
        #
        #     from smplkit import SmplClient, LogLevel
        #
        #     with SmplClient(environment="production", service="my-service") as client:
        #
        #         @client.logging.on_change("sqlalchemy.engine")
        #         def on_sql_change(event):
        #             print(f"SQL level changed to {event.level}")
        #
        #         client.logging.start()

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 8. CLEANUP
        # ==================================================================
        section("8. Cleanup")

        await teardown_demo_loggers(client.manage, demo)

        section("ALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
