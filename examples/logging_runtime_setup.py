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
    """Create demo loggers and groups. Returns a dict of keys for cleanup.

    Creates:
      - "databases" group: base=ERROR, production=WARN
      - "app" logger: managed, base=WARN, production=ERROR
      - "app.payments" logger: managed, no level (inherits from ancestor "app")
      - "sqlalchemy.engine" logger: managed, no level, assigned to "databases" group
    """
    environment = client._environment

    # Clean up leftover loggers and groups from previous runs.
    demo_logger_keys = {"app", "app.payments", "sqlalchemy.engine"}
    demo_group_keys = {"databases"}
    try:
        existing = await client.logging.list()
        for lg in existing:
            if lg.key in demo_logger_keys:
                await client.logging.delete(lg.key)
    except Exception:
        pass
    try:
        existing_groups = await client.logging.list_groups()
        for g in existing_groups:
            if g.key in demo_group_keys:
                await client.logging.delete_group(g.key)
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
        "logger_keys": ["app", "app.payments", "sqlalchemy.engine"],
        "group_keys": ["databases"],
    }


async def teardown_demo_loggers(client: AsyncSmplClient, demo: dict) -> None:
    """Delete demo loggers and groups."""
    for key in demo.get("logger_keys", []):
        try:
            await client.logging.delete(key)
        except Exception:
            pass

    for key in demo.get("group_keys", []):
        try:
            await client.logging.delete_group(key)
        except Exception:
            pass

    # Clean up any other loggers that were auto-discovered during the
    # runtime showcase (e.g., "app.notifications", SDK-internal loggers).
    try:
        remaining = await client.logging.list()
        for lg in remaining:
            await client.logging.delete(lg.key)
    except Exception:
        pass
