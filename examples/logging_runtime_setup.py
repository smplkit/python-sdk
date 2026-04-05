"""
Demo setup for the Logging Runtime Showcase.

Creates and configures managed loggers and log groups so the runtime
showcase can demonstrate auto-discovery, level resolution, and dynamic
control out of the box.

In a real application, loggers are auto-discovered and promoted via the
Console UI — this file exists only as test scaffolding.

See logging_management_showcase.py for the full management API walkthrough.
"""

from smplkit import AsyncSmplClient


async def setup_demo_loggers(client: AsyncSmplClient) -> dict:
    """Create demo loggers and groups. Returns a dict of objects for cleanup.

    Creates:
      - "databases" group: base=ERROR, production=WARN
      - "app" logger: managed, base=WARN, production=ERROR
      - "app.payments" logger: managed, no level (inherits from ancestor "app")
      - "sqlalchemy.engine" logger: managed, no level, assigned to "databases" group

    This mirrors what an admin would do in the Console after seeing
    auto-discovered loggers: promote them to managed, set levels, create
    groups, and assign loggers to groups.
    """
    environment = client._environment

    # Clean up leftover loggers and groups from previous runs.
    # Delete loggers first (groups can't be deleted while referenced).
    demo_logger_keys = {"app", "app.payments", "sqlalchemy.engine"}
    demo_group_keys = {"databases"}
    try:
        existing = await client.logging.list()
        for lg in existing:
            if lg.key in demo_logger_keys:
                await client.logging.delete(lg.id)
    except Exception:
        pass
    try:
        existing_groups = await client.logging.list_groups()
        for g in existing_groups:
            if g.key in demo_group_keys:
                await client.logging.delete_group(g.id)
    except Exception:
        pass

    # Create log group first (loggers will reference it).
    db_group = await client.logging.create_group(
        "databases",
        name="Databases",
        level="ERROR",
        environments={environment: {"level": "WARN"}},
    )

    # Create managed loggers.
    # "app" — the root application logger, with explicit levels.
    app_lg = await client.logging.create(
        "app",
        name="app",
        managed=True,
        level="WARN",
        environments={environment: {"level": "ERROR"}},
    )

    # "app.payments" — a child logger, no level set.
    # Will inherit from ancestor "app" via dot-notation resolution.
    payments_lg = await client.logging.create(
        "app.payments",
        name="app.payments",
        managed=True,
    )

    # "sqlalchemy.engine" — a database logger, no level set but in a group.
    # Will inherit from group "databases" via group chain resolution.
    sqla_lg = await client.logging.create(
        "sqlalchemy.engine",
        name="sqlalchemy.engine",
        managed=True,
        group=db_group.id,
    )

    return {
        "loggers": [app_lg, payments_lg, sqla_lg],
        "groups": [db_group],
    }


async def teardown_demo_loggers(client: AsyncSmplClient, demo: dict) -> None:
    """Delete demo loggers and groups."""
    for lg in demo.get("loggers", []):
        try:
            await client.logging.delete(lg.id)
        except Exception:
            pass  # May already be deleted

    for g in demo.get("groups", []):
        try:
            await client.logging.delete_group(g.id)
        except Exception:
            pass

    # Clean up any other loggers that were auto-discovered during the
    # runtime showcase (e.g., "app.notifications", SDK-internal loggers).
    try:
        remaining = await client.logging.list()
        for lg in remaining:
            await client.logging.delete(lg.id)
    except Exception:
        pass
