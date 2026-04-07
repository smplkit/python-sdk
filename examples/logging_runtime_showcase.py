"""
Smpl Logging SDK Showcase — Runtime
=====================================

Demonstrates the smplkit Python SDK's runtime experience for Smpl Logging:

- Automatic logger discovery via Python's ``logging`` module
- Explicit start() — opt-in monkey-patching and level management
- Level resolution chain: env override → base level → group → dot-notation → fallback
- Dynamic level control: server-side changes applied to the Python runtime
- @client.logging.on_change decorator with optional key scoping
- Continuous discovery (loggers created after start)

This is the SDK experience that 99%% of customers will use. Loggers are
discovered automatically and managed via the Console UI (or the
management API shown in ``logging_management_showcase.py``). This script
focuses entirely on the runtime: starting, discovering, resolving, and
reacting to changes.

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

# Demo scaffolding — creates server-side loggers and groups so this
# showcase can run standalone. In a real app, loggers are auto-discovered
# and promoted to managed via the Console UI.
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

    # ======================================================================
    # 0. APPLICATION LOGGERS
    # ======================================================================
    #
    # In a real application, loggers are created by your code and
    # libraries throughout the codebase. Here we simulate that.
    #
    # These Python loggers exist in the process BEFORE we call start().
    # When start() runs, the discovery engine scans the registry and
    # finds them.
    # ======================================================================

    stdlib_logging.getLogger("app").setLevel(stdlib_logging.INFO)
    stdlib_logging.getLogger("app.payments").setLevel(stdlib_logging.WARNING)
    stdlib_logging.getLogger("sqlalchemy.engine").setLevel(stdlib_logging.WARNING)

    # ======================================================================
    # 1. SDK INITIALIZATION + SETUP
    # ======================================================================
    section("1. SDK Initialization")

    ENVIRONMENT = "production"

    async with AsyncSmplClient(environment=ENVIRONMENT, service="showcase-service") as client:

        step(f"AsyncSmplClient initialized (environment={ENVIRONMENT}, service=showcase-service)")

        # Create server-side state (normally done via Console UI).
        print("  Setting up demo loggers and groups...")
        demo = await setup_demo_loggers(client)
        print("  Demo loggers ready.\n")

        # ==================================================================
        # 2. CHANGE LISTENERS — Register Before start()
        # ==================================================================
        #
        # @client.logging.on_change — fires when ANY logger/group changes
        # @client.logging.on_change("sqlalchemy.engine") — scoped to a key
        #
        # Listeners can be registered before start(). They are stored
        # locally and begin firing when WebSocket events arrive after start().
        # ==================================================================

        section("2. Register Change Listeners")

        all_changes: list = []

        @client.logging.on_change
        def on_any_change(event):
            all_changes.append(event)
            print(f"    [CHANGE] {event.key}: level={event.level}")

        step("Global change listener registered")

        sql_changes: list = []

        @client.logging.on_change("sqlalchemy.engine")
        def on_sql_change(event):
            sql_changes.append(event)
            print(f"    [SQL] sqlalchemy.engine level changed to {event.level}")

        step("Scoped listener registered for sqlalchemy.engine")

        # ==================================================================
        # 3. START — Discovery + Level Management
        # ==================================================================
        #
        # start() is the explicit opt-in for runtime logging control.
        # It performs:
        #   1. Scans logging.root.manager.loggerDict for existing loggers
        #   2. Installs monkey-patches for continuous discovery
        #   3. Bulk-registers discovered loggers with the server
        #   4. Fetches all logger and group definitions
        #   5. Resolves levels for managed loggers and applies them
        #   6. Opens the shared WebSocket for live updates
        #   7. Starts the periodic flush timer for new discoveries
        #
        # start() is idempotent — calling it multiple times is safe.
        # Management methods do NOT require start().
        # ==================================================================

        section("3. Auto-Discovery + Start")

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
        # 4. LEVEL RESOLUTION
        # ==================================================================
        #
        # The resolution chain (first non-null wins):
        #   1. Logger's own environment override
        #   2. Logger's own base level
        #   3. Group chain (recursive up the group hierarchy)
        #   4. Dot-notation ancestry (walk "app.payments" → "app")
        #   5. System fallback: INFO
        #
        # Resolution (in production environment):
        #   app              → step 1: production=ERROR → ERROR ✓
        #   app.payments     → steps 1-3: nothing → step 4: ancestor "app"
        #                      → "app" resolves to ERROR → ERROR ✓
        #   sqlalchemy.engine → steps 1-2: nothing → step 3: group "databases"
        #                       → "databases" production=WARN → WARN ✓
        # ==================================================================

        section("4. Level Resolution — Full Chain")

        step(f"  app → {python_level_name('app')}")
        step(f"    Resolution: env override ({ENVIRONMENT}=ERROR) ✓")

        step(f"\n  app.payments → {python_level_name('app.payments')}")
        step(f"    Resolution: no level → no group → ancestor 'app' → ERROR ✓")

        step(f"\n  sqlalchemy.engine → {python_level_name('sqlalchemy.engine')}")
        step(f"    Resolution: no level → group 'databases' → env override ({ENVIRONMENT}=WARN) ✓")

        # ==================================================================
        # 5. DYNAMIC LEVEL CONTROL
        # ==================================================================
        #
        # Change a level on the server via management API. In production,
        # WebSocket events trigger re-resolution automatically. Here we
        # use a brief sleep to let the WebSocket deliver the update.
        # ==================================================================

        # ------------------------------------------------------------------
        # 5a. Change a group level — all members shift
        # ------------------------------------------------------------------
        section("5a. Dynamic Control — Change Group Level")

        db_group = await client.logging.get_group("databases")
        step(f"sqlalchemy.engine before: {python_level_name('sqlalchemy.engine')}")

        db_group.setEnvironmentLevel(ENVIRONMENT, LogLevel.DEBUG)
        await db_group.save()
        step(f"Changed databases group {ENVIRONMENT} override: WARN → DEBUG")

        await asyncio.sleep(2)

        step(f"sqlalchemy.engine after: {python_level_name('sqlalchemy.engine')}")
        step("  Group-level change cascaded to all group members")

        # ------------------------------------------------------------------
        # 5b. Change an ancestor level — dot-notation children shift
        # ------------------------------------------------------------------
        section("5b. Dynamic Control — Change Ancestor Level")

        app_lg = await client.logging.get("app")
        step(f"app.payments before: {python_level_name('app.payments')}")

        app_lg.setEnvironmentLevel(ENVIRONMENT, LogLevel.TRACE)
        await app_lg.save()
        step(f"Changed app {ENVIRONMENT} override: ERROR → TRACE")

        await asyncio.sleep(2)

        step(f"app after: {python_level_name('app')}")
        step(f"app.payments after: {python_level_name('app.payments')}")
        step("  Ancestor-level change cascaded via dot-notation hierarchy")

        # ------------------------------------------------------------------
        # 5c. Clear an environment override — falls through to base level
        # ------------------------------------------------------------------
        section("5c. Dynamic Control — Clear Override")

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
        # 6. CONTINUOUS DISCOVERY
        # ==================================================================
        #
        # The monkey-patches installed during start() intercept:
        #   - logging.Manager.getLogger → detects new loggers
        #   - logging.Logger.setLevel  → detects runtime level changes
        #
        # New loggers are queued and bulk-registered on the next periodic
        # flush (every 5 seconds).
        # ==================================================================

        section("6. Continuous Discovery")

        step("Creating a new Python logger after start()...")
        new_logger = stdlib_logging.getLogger("app.notifications")
        new_logger.setLevel(stdlib_logging.INFO)
        step("Created: app.notifications (INFO)")
        step("The SDK intercepted this and queued it for bulk registration.")
        step("It will appear on the server after the next periodic flush (~5s).")

        # ==================================================================
        # 7. CHANGE LISTENER RESULTS
        # ==================================================================
        section("7. Change Listener Results")

        step(f"Global changes received: {len(all_changes)}")
        step(f"SQL-specific changes received: {len(sql_changes)}")

        # ==================================================================
        # 8. SYNC CLIENT DEMO
        # ==================================================================
        section("8. Sync Client (same API, no await)")

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
        #         client.logging.start()  # discovers loggers, applies levels
        #
        #         # Your application runs — loggers are being controlled.
        #         # New loggers are auto-discovered. Level changes are reported.

        step("(See code comments for sync usage examples)")

        # ==================================================================
        # 9. CLEANUP
        # ==================================================================
        section("9. Cleanup")

        await teardown_demo_loggers(client, demo)
        step("Demo loggers and groups deleted")

        # ==================================================================
        # DONE
        # ==================================================================
        section("ALL DONE")
        print("  The Logging Runtime showcase completed successfully.")
        print("  If you got here, Smpl Logging is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
