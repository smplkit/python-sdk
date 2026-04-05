"""
Demo setup for the Config Runtime Showcase.

Creates and configures a config hierarchy so the runtime showcase can
demonstrate prescriptive resolution, typed accessors, inheritance, and
change listeners out of the box.

In a real application, configs are created and maintained via the Console
UI (or the management API shown in ``config_management_showcase.py``).
This file exists only as test scaffolding.

See config_management_showcase.py for the full management API walkthrough.
"""

from smplkit import AsyncSmplClient


async def setup_demo_configs(client: AsyncSmplClient) -> dict:
    """Create demo configs. Returns a dict of objects for cleanup.

    Creates:
      - Updates "common" config with org-wide defaults + env overrides
      - "user_service" config: service-specific items (inherits from common)
      - "auth_module" config: child of user_service (multi-level inheritance)

    This mirrors what an admin would do in the Console: define a config
    hierarchy with base values and environment-specific overrides.
    """
    environment = client._environment

    # Update the built-in common config with org-wide defaults.
    common = await client.config.get(key="common")
    await common.update(
        description="Organization-wide shared configuration",
        items={
            "app_name": {"value": "Acme SaaS Platform", "type": "STRING"},
            "support_email": {"value": "support@acme.dev", "type": "STRING"},
            "max_retries": {"value": 3, "type": "NUMBER"},
            "request_timeout_ms": {"value": 5000, "type": "NUMBER"},
            "pagination_default_page_size": {"value": 25, "type": "NUMBER"},
        },
    )
    await common.set_values(
        {"max_retries": 5, "request_timeout_ms": 10000},
        environment="production",
    )
    await common.set_values(
        {"max_retries": 2},
        environment="staging",
    )

    # Create a service-specific config (inherits from common).
    user_service = await client.config.create(
        name="User Service",
        key="user_service",
        description="Configuration for the user microservice.",
        items={
            "database": {"value": {"host": "localhost", "port": 5432, "name": "users_dev", "pool_size": 5}},
            "cache_ttl_seconds": {"value": 300, "type": "NUMBER"},
            "enable_signup": {"value": True, "type": "BOOLEAN"},
            "pagination_default_page_size": {"value": 50, "type": "NUMBER"},
        },
    )
    await user_service.set_values(
        {
            "database": {"host": "prod-users-rds.internal.acme.dev", "name": "users_prod", "pool_size": 20},
            "cache_ttl_seconds": 600,
        },
        environment="production",
    )
    await user_service.set_value("enable_signup", False, environment="production")

    # Create a child config for multi-level inheritance.
    auth_module = await client.config.create(
        name="Auth Module",
        key="auth_module",
        description="Authentication module within the user service.",
        parent=user_service.id,
        items={
            "session_ttl_minutes": {"value": 60, "type": "NUMBER"},
            "mfa_enabled": {"value": False, "type": "BOOLEAN"},
        },
    )
    await auth_module.set_values(
        {"session_ttl_minutes": 30, "mfa_enabled": True},
        environment="production",
    )

    return {
        "configs": [user_service, auth_module],
        "common": common,
    }


async def teardown_demo_configs(client: AsyncSmplClient, demo: dict) -> None:
    """Delete demo configs and reset common."""
    for cfg in demo.get("configs", []):
        try:
            await client.config.delete(cfg.id)
        except Exception:
            pass  # May already be deleted

    # Reset common config to empty.
    common = demo.get("common")
    if common:
        try:
            await common.update(description="", items={}, environments={})
        except Exception:
            pass
