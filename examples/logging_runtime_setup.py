"""
Demo setup for the Logging Runtime Showcase.

Creates and configures managed loggers and log groups so the runtime
showcase can demonstrate auto-discovery, level resolution, and dynamic
control out of the box.

In a real application, loggers are auto-discovered and promoted via the
Console UI — this file exists only as test scaffolding.
"""

from smplkit import AsyncSmplClient, LogLevel


async def setup_demo_loggers(client: AsyncSmplClient) -> dict:
    """Create demo loggers and groups. Returns a dict of ids for cleanup.

    Creates:
      - "databases" group: base=ERROR, production=WARN
      - "app" logger: managed, base=WARN, production=ERROR
      - "app.payments" logger: managed, no level (inherits from ancestor "app")
      - "sqlalchemy.engine" logger: managed, no level, assigned to "databases" group
    """
    environment = client._environment

    # Clean up leftover loggers and groups from previous runs.
    demo_logger_ids = {"app", "app.payments", "sqlalchemy.engine"}
    demo_group_ids = {"databases"}
    try:
        existing = await client.logging.list()
        for lg in existing:
            if lg.id in demo_logger_ids:
                await client.logging.delete(lg.id)
    except Exception:
        pass
    try:
        existing_groups = await client.logging.list_groups()
        for g in existing_groups:
            # Server assigns group IDs from the name (e.g. "Databases"), normalize for comparison
            if g.id.lower().replace(" ", "_") in demo_group_ids:
                await client.logging.delete_group(g.id)
    except Exception:
        pass

    # Create log group first (loggers will reference it).
    db_group = client.logging.new_group("databases", name="Databases")
    db_group.setLevel(LogLevel.ERROR)
    db_group.setEnvironmentLevel(environment, LogLevel.WARN)
    await db_group.save()

    # Create managed loggers.
    app_lg = client.logging.new("app", name="app", managed=True)
    app_lg.setLevel(LogLevel.WARN)
    app_lg.setEnvironmentLevel(environment, LogLevel.ERROR)
    await app_lg.save()

    payments_lg = client.logging.new("app.payments", name="app.payments", managed=True)
    await payments_lg.save()

    sqla_lg = client.logging.new("sqlalchemy.engine", name="sqlalchemy.engine", managed=True)
    sqla_lg.group = db_group.id
    await sqla_lg.save()

    return {
        "logger_ids": [app_lg.id, payments_lg.id, sqla_lg.id],
        "group_ids": [db_group.id],  # server-assigned id (e.g. "Databases")
    }


async def teardown_demo_loggers(client: AsyncSmplClient, demo: dict) -> None:
    """Delete demo loggers and groups."""
    for id in demo.get("logger_ids", []):
        try:
            await client.logging.delete(id)
        except Exception:
            pass

    for id in demo.get("group_ids", []):
        try:
            await client.logging.delete_group(id)
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
