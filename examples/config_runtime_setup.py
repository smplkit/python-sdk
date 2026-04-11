"""
Demo setup for the Config Runtime Showcase.

Creates and configures a config hierarchy so the runtime showcase can
demonstrate resolve(), subscribe(), inheritance, and change listeners.

In a real application, configs are created and maintained via the Console
UI (or the management API shown in ``config_management_showcase.py``).
This file exists only as test scaffolding.
"""

from smplkit import AsyncSmplClient


async def setup_demo_configs(client: AsyncSmplClient) -> dict:
    """Create demo configs. Returns a dict of ids for cleanup.

    Creates:
      - Updates "common" config with org-wide defaults + env overrides
      - "user_service" config: service-specific items (inherits from common)
      - "auth_module" config: auth-specific items (inherits from common)
    """
    # Clean up leftover configs from previous runs (order matters: children first).
    for leftover_key in ("auth_module", "user_service"):
        try:
            await client.config.delete(leftover_key)
        except Exception:
            pass

    # Update the built-in common config with org-wide defaults.
    # Reset items first to avoid type-change errors from previous runs.
    common = await client.config.get("common")
    common.description = ""
    common.items = {}
    common.environments = {}
    await common.save()

    common.description = "Organization-wide shared configuration"
    common.items = {
        "app_name": {"value": "Acme SaaS Platform", "type": "STRING"},
        "support_email": {"value": "support@acme.dev", "type": "STRING"},
        "max_retries": {"value": 3, "type": "NUMBER"},
        "request_timeout_ms": {"value": 5000, "type": "NUMBER"},
        "pagination_default_page_size": {"value": 25, "type": "NUMBER"},
    }
    common.environments = {
        "production": {
            "values": {
                "max_retries": {"value": 5},
                "request_timeout_ms": {"value": 10000},
            },
        },
        "staging": {
            "values": {
                "max_retries": {"value": 2},
            },
        },
    }
    await common.save()

    # Create a service-specific config (inherits from common).
    user_service = client.config.new(
        "user_service",
        name="User Service",
        description="Configuration for the user microservice.",
    )
    user_service.items = {
        "database.host": {"value": "localhost", "type": "STRING"},
        "database.port": {"value": 5432, "type": "NUMBER"},
        "database.name": {"value": "users_dev", "type": "STRING"},
        "database.pool_size": {"value": 5, "type": "NUMBER"},
        "cache_ttl_seconds": {"value": 300, "type": "NUMBER"},
        "enable_signup": {"value": True, "type": "BOOLEAN"},
        "pagination_default_page_size": {"value": 50, "type": "NUMBER"},
    }
    user_service.environments = {
        "production": {
            "values": {
                "database.host": {"value": "prod-users-rds.internal.acme.dev"},
                "database.name": {"value": "users_prod"},
                "database.pool_size": {"value": 20},
                "cache_ttl_seconds": {"value": 600},
                "enable_signup": {"value": False},
            },
        },
    }
    await user_service.save()

    # Create auth_module config (also inherits from common).
    auth_module = client.config.new(
        "auth_module",
        name="Auth Module",
        description="Authentication module within the user service.",
    )
    auth_module.items = {
        "session_ttl_minutes": {"value": 60, "type": "NUMBER"},
        "mfa_enabled": {"value": False, "type": "BOOLEAN"},
    }
    auth_module.environments = {
        "production": {
            "values": {
                "session_ttl_minutes": {"value": 30},
                "mfa_enabled": {"value": True},
            },
        },
    }
    await auth_module.save()

    return {
        "config_ids": ["user_service", "auth_module"],
        "common_id": "common",
    }


async def teardown_demo_configs(client: AsyncSmplClient, demo: dict) -> None:
    """Delete demo configs and reset common."""
    for id in demo.get("config_ids", []):
        try:
            await client.config.delete(id)
        except Exception:
            pass

    # Reset common config to empty.
    try:
        common = await client.config.get(demo["common_id"])
        common.description = ""
        common.items = {}
        common.environments = {}
        await common.save()
    except Exception:
        pass
