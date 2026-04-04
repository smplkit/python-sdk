"""
Smpl Logging SDK Showcase — Runtime
=====================================

Demonstrates the smplkit Python SDK's runtime experience for Smpl Logging:

- Automatic logger discovery via Python's ``logging`` module
- Auto-discovered loggers matching server-side managed loggers
- Level resolution chain: env override → base level → group → dot-notation → fallback
- Dynamic level control: server-side changes applied to the Python runtime
- Manual refresh: ``client.logging.refresh()``
- Continuous discovery (loggers created after connect)
- Runtime level change detection

This is the SDK experience that 99%% of customers will use. Loggers are
discovered automatically and managed via the Console UI (or the
management API shown in ``logging_management_showcase.py``). This script
focuses entirely on the runtime: connecting, discovering, resolving, and
reacting to changes.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key (set via ``SMPLKIT_API_KEY`` env var)
    - The smplkit Logging service running and reachable

Usage::

    export SMPLKIT_API_KEY="sk_api_..."
    export SMPLKIT_ENVIRONMENT="production"
    export SMPLKIT_SERVICE="showcase-service"
    python examples/logging_runtime_showcase.py
"""

import asyncio
import logging as stdlib_logging
import os
import sys

from smplkit import AsyncSmplClient

# Demo scaffolding — creates server-side loggers and groups so this
# showcase can run standalone. In a real app, loggers are auto-discovered
# and promoted to managed via the Console UI.
from logging_runtime_setup import setup_demo_loggers, teardown_demo_loggers

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("SMPLKIT_API_KEY", "")
ENVIRONMENT = os.environ.get("SMPLKIT_ENVIRONMENT", "production")
SERVICE = os.environ.get("SMPLKIT_SERVICE", "showcase-service")

if not API_KEY:
    print("ERROR: Set the SMPLKIT_API_KEY environment variable before running.")
    print("  export SMPLKIT_API_KEY='sk_api_...'")
    sys.exit(1)

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
    # These Python loggers exist in the process BEFORE we connect the
    # smplkit SDK. When connect() runs, the discovery engine scans the
    # registry and finds them.
    #
    # ======================================================================

    stdlib_logging.getLogger("app").setLevel(stdlib_logging.INFO)
    stdlib_logging.getLogger("app.payments").setLevel(stdlib_logging.WARNING)
    stdlib_logging.getLogger("sqlalchemy.engine").setLevel(stdlib_logging.WARNING)

    # ======================================================================
    # 1. SDK INITIALIZATION + SETUP
    # ======================================================================
    section("1. SDK Initialization")

    client = AsyncSmplClient(
        API_KEY,
        environment=ENVIRONMENT,
        service=SERVICE,
    )
    step(f"AsyncSmplClient initialized (environment={ENVIRONMENT}, service={SERVICE})")

    # Create server-side state (normally done via Console UI).
    print("  Setting up demo loggers and groups...")
    demo = await setup_demo_loggers(client)
    print("  Demo loggers ready.\n")

    # The server now has:
    #   "app"              — managed, base=WARN, production=ERROR
    #   "app.payments"     — managed, level=NULL (inherits from ancestor)
    #   "sqlalchemy.engine" — managed, level=NULL, group="databases"
    #   "databases" group  — base=ERROR, production=WARN

    # ======================================================================
    # 2. AUTO-DISCOVERY + CONNECT
    # ======================================================================
    #
    # connect() does the following for logging:
    #
    #   1. Scans logging.root.manager.loggerDict — finds "app",
    #      "app.payments", "sqlalchemy.engine" (plus SDK-internal loggers).
    #   2. Monkey-patches Manager.getLogger for continuous discovery.
    #   3. Monkey-patches Logger.setLevel for runtime change detection.
    #   4. Bulk-registers discovered loggers. The server finds existing
    #      rows (created by setup) and updates their sources array
    #      with this service+environment pair and the observed levels.
    #   5. Fetches all logger and group data from the server.
    #   6. Resolves effective levels for managed loggers and applies
    #      them to the Python runtime via setLevel().
    #
    # ======================================================================

    section("2. Auto-Discovery + Connect")

    step("Python levels before connect (application defaults):")
    for name in ["app", "app.payments", "sqlalchemy.engine"]:
        step(f"  {name}: {python_level_name(name)}")
    # Expected: INFO, WARNING, WARNING

    await client.connect()
    step("\nclient.connect() completed")

    step("\nPython levels after connect (smplkit has taken control):")
    for name in ["app", "app.payments", "sqlalchemy.engine"]:
        step(f"  {name}: {python_level_name(name)}")
    # Expected: ERROR, ERROR, WARNING — resolved per the chain below

    # ======================================================================
    # 3. LEVEL RESOLUTION
    # ======================================================================
    #
    # The resolution chain (first non-null wins):
    #
    #   1. Logger's own environment override
    #   2. Logger's own base level
    #   3. Group chain (recursive up the group hierarchy)
    #   4. Dot-notation ancestry (walk "app.payments" → "app")
    #   5. System fallback: INFO
    #
    # Current server state:
    #   app              — base=WARN, production=ERROR
    #   app.payments     — level=NULL, no group
    #   sqlalchemy.engine — level=NULL, group="databases"
    #   "databases" group — base=ERROR, production=WARN
    #
    # Resolution (in production environment):
    #   app              → step 1: production=ERROR → ERROR ✓
    #   app.payments     → steps 1-3: nothing → step 4: ancestor "app"
    #                      → "app" resolves to ERROR → ERROR ✓
    #   sqlalchemy.engine → steps 1-2: nothing → step 3: group "databases"
    #                       → "databases" production=WARN → WARN ✓
    #
    # ======================================================================

    section("3. Level Resolution — Full Chain")

    step(f"  app → {python_level_name('app')}")
    step(f"    Resolution: env override ({ENVIRONMENT}=ERROR) ✓")

    step(f"\n  app.payments → {python_level_name('app.payments')}")
    step(f"    Resolution: no level → no group → ancestor 'app' → ERROR ✓")

    step(f"\n  sqlalchemy.engine → {python_level_name('sqlalchemy.engine')}")
    step(f"    Resolution: no level → group 'databases' "
         f"→ env override ({ENVIRONMENT}=WARN) ✓")

    # ======================================================================
    # 4. DYNAMIC LEVEL CONTROL
    # ======================================================================
    #
    # Change a level on the server, call refresh(), and the Python
    # runtime reflects the change instantly. In production, WebSocket
    # events trigger this automatically — no manual refresh() needed.
    #
    # ======================================================================

    # ------------------------------------------------------------------
    # 4a. Change a group level — all members shift
    # ------------------------------------------------------------------
    section("4a. Dynamic Control — Change Group Level")

    db_group = demo["groups"][0]
    step(f"sqlalchemy.engine before: {python_level_name('sqlalchemy.engine')}")

    await client.logging.update_group(
        db_group.id,
        environments={ENVIRONMENT: {"level": "DEBUG"}},
    )
    step(f"Changed databases group {ENVIRONMENT} override: WARN → DEBUG")

    await client.logging.refresh()
    step("client.logging.refresh()")

    step(f"sqlalchemy.engine after: {python_level_name('sqlalchemy.engine')}")
    step("  Group-level change cascaded to all group members")

    # ------------------------------------------------------------------
    # 4b. Change an ancestor level — dot-notation children shift
    # ------------------------------------------------------------------
    section("4b. Dynamic Control — Change Ancestor Level")

    app_lg = demo["loggers"][0]
    step(f"app.payments before: {python_level_name('app.payments')}")

    await client.logging.update(
        app_lg.id,
        environments={ENVIRONMENT: {"level": "TRACE"}},
    )
    step(f"Changed app {ENVIRONMENT} override: ERROR → TRACE")

    await client.logging.refresh()
    step("client.logging.refresh()")

    step(f"app after: {python_level_name('app')}")
    step(f"app.payments after: {python_level_name('app.payments')}")
    step("  Ancestor-level change cascaded via dot-notation hierarchy")

    # ------------------------------------------------------------------
    # 4c. Clear an environment override — falls through to base level
    # ------------------------------------------------------------------
    section("4c. Dynamic Control — Clear Override")

    step(f"app before: {python_level_name('app')}")

    await client.logging.update(app_lg.id, environments={})
    step("Cleared all env overrides on app")

    await client.logging.refresh()
    step("client.logging.refresh()")

    step(f"app after: {python_level_name('app')}")
    # Expected: WARNING — no env override, falls through to base level (WARN)

    step(f"app.payments after: {python_level_name('app.payments')}")
    # Expected: WARNING — inherits from ancestor "app"

    # ======================================================================
    # 5. CONTINUOUS DISCOVERY
    # ======================================================================
    #
    # The monkey-patches installed during connect() intercept:
    #   - logging.Manager.getLogger → detects new loggers
    #   - logging.Logger.setLevel  → detects runtime level changes
    #
    # New loggers are queued and bulk-registered on the next periodic
    # flush (every 5 seconds). They land as unmanaged on the server
    # and appear in the Console for the admin to review.
    #
    # Level changes on existing loggers are reported back so the
    # Console stays current even for unmanaged loggers.
    #
    # ======================================================================

    section("5. Continuous Discovery")

    step("Creating a new Python logger after connect()...")
    new_logger = stdlib_logging.getLogger("app.notifications")
    new_logger.setLevel(stdlib_logging.INFO)
    step("Created: app.notifications (INFO)")
    step("The SDK intercepted this and queued it for bulk registration.")
    step("It will appear on the server after the next periodic flush (~5s).")

    step("\nChanging an existing logger's level at runtime...")
    stdlib_logging.getLogger("app").setLevel(stdlib_logging.DEBUG)
    step("Changed app level to DEBUG via Python setLevel()")
    step("The SDK intercepted this change and will report it to the server.")
    step("(This does not affect smplkit's managed-level resolution — the")
    step(" next refresh() will reapply the server-configured level.)")

    # ======================================================================
    # 6. SYNC CLIENT DEMO
    # ======================================================================
    section("6. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools):
    #
    #     from smplkit import SmplClient
    #
    #     client = SmplClient(
    #         "sk_api_...",
    #         environment="production",
    #         service="my-service",
    #     )
    #     client.connect()  # discovers loggers, applies managed levels
    #
    #     # Your application runs — loggers are being controlled.
    #     # New loggers are auto-discovered. Level changes are reported.
    #
    #     client.logging.refresh()  # manually re-fetch + re-apply
    #
    #     client.close()

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 7. CLEANUP
    # ======================================================================
    section("7. Cleanup")

    await teardown_demo_loggers(client, demo)
    step("Demo loggers and groups deleted")

    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Logging Runtime showcase completed successfully.")
    print("  If you got here, Smpl Logging is ready to ship.\n")


if __name__ == "__main__":
    asyncio.run(main())
