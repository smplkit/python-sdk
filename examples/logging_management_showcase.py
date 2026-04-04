"""
Smpl Logging SDK Showcase — Management API
============================================

Demonstrates the smplkit Python SDK's management plane for Smpl Logging:

- Logger inspection: list and get auto-discovered loggers
- Promote / release: toggling ``managed`` status
- Direct level control: base levels and environment overrides
- Clear-field semantics: setting level back to NULL for inheritance
- Log group CRUD: create, list, get, update, delete
- Group assignment: assigning loggers to groups
- Manual logger creation

Most customers will manage loggers via the Console UI. This showcase
demonstrates the programmatic equivalent — useful for infrastructure-
as-code, CI/CD pipelines, setup scripts, and automated testing.

For the runtime experience (auto-discovery, connect, level resolution,
dynamic control, continuous discovery), see ``logging_runtime_showcase.py``.

**Free-plan limits:** This showcase is designed to run within free-plan
entitlements: ≤ 5 managed loggers, ≤ 3 log groups, nesting depth = 1
(flat groups only).

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key (set via ``SMPLKIT_API_KEY`` env var)
    - The smplkit Logging service running and reachable

Usage::

    export SMPLKIT_API_KEY="sk_api_..."
    export SMPLKIT_ENVIRONMENT="production"
    export SMPLKIT_SERVICE="showcase-service"
    python examples/logging_management_showcase.py
"""

import asyncio
import os
import sys

from smplkit import AsyncSmplClient

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


async def main() -> None:

    # ======================================================================
    # 1. SDK INITIALIZATION
    # ======================================================================
    section("1. SDK Initialization")

    # Management operations do not require connect() — they are
    # stateless API calls. But the constructor still requires all
    # three parameters (api_key, environment, service).
    client = AsyncSmplClient(
        API_KEY,
        environment=ENVIRONMENT,
        service=SERVICE,
    )
    step(f"AsyncSmplClient initialized (environment={ENVIRONMENT}, service={SERVICE})")

    # ======================================================================
    # 2. MANUAL LOGGER CREATION
    # ======================================================================
    #
    # client.logging.create() creates a logger via POST /api/v1/loggers.
    #
    # The managed field controls entitlement enforcement:
    #   managed=True  → consumes a logging.managed_loggers slot
    #   managed=False → no slot consumed (same as auto-discovery)
    #
    # In production, most loggers are auto-discovered. Manual creation
    # is useful for:
    #   - Creating control points (e.g., a dot-notation parent that no
    #     service has instantiated yet)
    #   - Infrastructure-as-code / scripted setup
    #   - Testing
    #
    # ======================================================================

    section("2a. Create Managed Loggers")

    app_lg = await client.logging.create(
        "app",
        name="app",
        managed=True,
        level="WARN",
    )
    step(f"Created: key={app_lg.key}, managed={app_lg.managed}, level={app_lg.level}")

    payments_lg = await client.logging.create(
        "app.payments",
        name="app.payments",
        managed=True,
        # No level — will inherit via dot-notation from "app"
    )
    step(f"Created: key={payments_lg.key}, managed={payments_lg.managed}, "
         f"level={payments_lg.level or '(null)'}")

    sqla_lg = await client.logging.create(
        "sqlalchemy.engine",
        name="sqlalchemy.engine",
        managed=True,
    )
    step(f"Created: key={sqla_lg.key}, managed={sqla_lg.managed}, "
         f"level={sqla_lg.level or '(null)'}")

    section("2b. Create an Unmanaged Logger")

    unmanaged_lg = await client.logging.create(
        "app.internal.debug",
        name="app.internal.debug",
        managed=False,
    )
    step(f"Created: key={unmanaged_lg.key}, managed={unmanaged_lg.managed}")
    step("  Unmanaged loggers do not consume managed-logger slots")

    # ======================================================================
    # 3. LOGGER INSPECTION
    # ======================================================================

    # ------------------------------------------------------------------
    # 3a. List all loggers
    # ------------------------------------------------------------------
    section("3a. List All Loggers")

    loggers = await client.logging.list()
    step(f"Total loggers: {len(loggers)}")
    for lg in loggers:
        step(f"  {lg.key} (managed={lg.managed}, level={lg.level or '(null)'})")

    # ------------------------------------------------------------------
    # 3b. Get a single logger by ID
    # ------------------------------------------------------------------
    section("3b. Get a Logger by ID")

    fetched = await client.logging.get(app_lg.id)
    step(f"Fetched: key={fetched.key}, name={fetched.name}")
    step(f"  managed={fetched.managed}")
    step(f"  level={fetched.level}")
    step(f"  environments={fetched.environments}")
    step(f"  sources={fetched.sources}")

    # ======================================================================
    # 4. DIRECT LEVEL CONTROL
    # ======================================================================

    # ------------------------------------------------------------------
    # 4a. Set a base level
    # ------------------------------------------------------------------
    section("4a. Set Base Level")

    await client.logging.update(sqla_lg.id, level="ERROR")
    sqla_lg = await client.logging.get(sqla_lg.id)
    step(f"Set sqlalchemy.engine base level → {sqla_lg.level}")

    # ------------------------------------------------------------------
    # 4b. Set environment overrides
    # ------------------------------------------------------------------
    section("4b. Set Environment Overrides")

    await client.logging.update(
        app_lg.id,
        environments={
            "production": {"level": "ERROR"},
            "staging": {"level": "DEBUG"},
        },
    )
    app_lg = await client.logging.get(app_lg.id)
    step(f"Set app environment overrides: {app_lg.environments}")
    step("  production → ERROR, staging → DEBUG, other envs → base (WARN)")

    # ------------------------------------------------------------------
    # 4c. Clear a level (set back to null for inheritance)
    # ------------------------------------------------------------------
    section("4c. Clear Level — Restore Inheritance")

    # Passing level=None explicitly clears the logger's base level
    # back to NULL. This is distinct from omitting the parameter
    # entirely (which preserves the existing value).
    #
    # With level=NULL, the logger inherits from its group,
    # dot-notation ancestor, or the system default (INFO).
    await client.logging.update(sqla_lg.id, level=None)
    sqla_lg = await client.logging.get(sqla_lg.id)
    step(f"Cleared sqlalchemy.engine level → {sqla_lg.level or '(null)'}")
    step("  Now inherits from group, dot-notation ancestor, or system default")

    # Clear env overrides by sending an empty dict.
    await client.logging.update(app_lg.id, environments={})
    app_lg = await client.logging.get(app_lg.id)
    step(f"Cleared app env overrides → {app_lg.environments}")

    # ======================================================================
    # 5. LOG GROUP CRUD
    # ======================================================================

    # ------------------------------------------------------------------
    # 5a. Create log groups
    # ------------------------------------------------------------------
    section("5a. Create Log Groups")

    db_group = await client.logging.create_group(
        "databases",
        name="Databases",
        level="ERROR",
        environments={"production": {"level": "WARN"}},
    )
    step(f"Created group: key={db_group.key}, id={db_group.id}")
    step(f"  level=ERROR, production override=WARN")

    http_group = await client.logging.create_group(
        "http_clients",
        name="HTTP Clients",
        level="INFO",
    )
    step(f"Created group: key={http_group.key}, id={http_group.id}")

    # ------------------------------------------------------------------
    # 5b. List log groups
    # ------------------------------------------------------------------
    section("5b. List Log Groups")

    groups = await client.logging.list_groups()
    step(f"Total groups: {len(groups)}")
    for g in groups:
        env_str = f", envs={g.environments}" if g.environments else ""
        step(f"  {g.key}: level={g.level}{env_str}")

    # ------------------------------------------------------------------
    # 5c. Get a single group by ID
    # ------------------------------------------------------------------
    section("5c. Get a Log Group by ID")

    fetched_group = await client.logging.get_group(db_group.id)
    step(f"Fetched: key={fetched_group.key}, name={fetched_group.name}")
    step(f"  level={fetched_group.level}")
    step(f"  environments={fetched_group.environments}")

    # ------------------------------------------------------------------
    # 5d. Update a group
    # ------------------------------------------------------------------
    section("5d. Update a Log Group")

    http_group = await client.logging.update_group(
        http_group.id,
        level="DEBUG",
        environments={"production": {"level": "WARN"}},
    )
    step(f"Updated {http_group.key}: level={http_group.level}, "
         f"envs={http_group.environments}")

    # ======================================================================
    # 6. GROUP ASSIGNMENT
    # ======================================================================
    section("6. Group Assignment")

    # Assign a logger to a group via update.
    await client.logging.update(sqla_lg.id, group=db_group.id)
    sqla_lg = await client.logging.get(sqla_lg.id)
    step(f"Assigned sqlalchemy.engine → group '{db_group.key}'")
    step(f"  group={sqla_lg.group}")
    step("  Managed state unchanged — group assignment does not affect managed status")

    # Unassign by clearing group to null.
    await client.logging.update(sqla_lg.id, group=None)
    sqla_lg = await client.logging.get(sqla_lg.id)
    step(f"\nUnassigned sqlalchemy.engine from group")
    step(f"  group={sqla_lg.group or '(null)'}")

    # Re-assign for the remaining demo.
    await client.logging.update(sqla_lg.id, group=db_group.id)
    step(f"Re-assigned sqlalchemy.engine → group '{db_group.key}'")

    # ======================================================================
    # 7. PROMOTE / RELEASE
    # ======================================================================
    #
    # Promoting a logger (managed=false → true) consumes a managed
    # slot. Releasing (managed=true → false) frees a slot and clears
    # level, environments, and group_id — returning the logger to its
    # unmanaged, observed-only state.
    #
    # ======================================================================
    section("7a. Release a Managed Logger")

    step(f"Before: key={sqla_lg.key}, managed={sqla_lg.managed}, "
         f"level={sqla_lg.level or '(null)'}, group={sqla_lg.group}")

    await client.logging.update(sqla_lg.id, managed=False)
    sqla_lg = await client.logging.get(sqla_lg.id)
    step("Released sqlalchemy.engine → unmanaged")
    step(f"After: managed={sqla_lg.managed}, level={sqla_lg.level or '(null)'}, "
         f"group={sqla_lg.group or '(null)'}, environments={sqla_lg.environments}")
    # Expected: managed=false, level=null, group=null, environments={}

    section("7b. Re-Promote a Logger")

    await client.logging.update(sqla_lg.id, managed=True)
    sqla_lg = await client.logging.get(sqla_lg.id)
    step(f"Re-promoted: managed={sqla_lg.managed}")
    step("  Starts fresh with level=NULL — admin configures from here")

    # ======================================================================
    # 8. SYNC CLIENT DEMO
    # ======================================================================
    section("8. Sync Client (same API, no await)")

    # For sync applications (Django, Flask, CLI tools):
    #
    #     from smplkit import SmplClient
    #
    #     client = SmplClient(
    #         "sk_api_...",
    #         environment="production",
    #         service="my-service",
    #     )
    #
    #     # Management API (no connect() needed)
    #     loggers = client.logging.list()
    #     client.logging.update(logger_id, managed=True)
    #     group = client.logging.create_group(
    #         "sql", name="SQL Loggers", level="WARN",
    #     )
    #     client.logging.update(logger_id, group=group.id)
    #     client.logging.update(logger_id, managed=False)  # release
    #     client.logging.delete_group(group.id)
    #
    #     client.close()

    step("(See code comments for sync usage examples)")

    # ======================================================================
    # 9. CLEANUP
    # ======================================================================
    section("9. Cleanup")

    # Delete log groups (server automatically unparents member loggers).
    await client.logging.delete_group(db_group.id)
    step(f"Deleted group: {db_group.key}")

    await client.logging.delete_group(http_group.id)
    step(f"Deleted group: {http_group.key}")

    # Delete all loggers.
    for lg in [app_lg, payments_lg, sqla_lg, unmanaged_lg]:
        await client.logging.delete(lg.id)
        step(f"Deleted logger: {lg.key}")

    await client.close()
    step("AsyncSmplClient closed")

    # ======================================================================
    # DONE
    # ======================================================================
    section("ALL DONE")
    print("  The Logging Management showcase completed successfully.")
    print("  All loggers and log groups have been cleaned up.\n")


if __name__ == "__main__":
    asyncio.run(main())
