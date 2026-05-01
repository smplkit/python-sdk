"""Setup / cleanup helpers for ``config_runtime_showcase.py``."""

from __future__ import annotations

from smplkit import AsyncSmplManagementClient, NotFoundError

_DEMO_ENVIRONMENTS = ["staging", "production"]
_DEMO_CONFIG_IDS = ["showcase-user-service", "showcase-auth-module", "showcase-common"]


async def setup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
    existing = {env.id for env in await manage.environments.list()}
    for env_id in _DEMO_ENVIRONMENTS:
        if env_id not in existing:
            await manage.environments.new(env_id, name=env_id.title()).save()
    await cleanup_runtime_showcase(manage)

    shared = manage.config.new(
        "showcase-common",
        name="Showcase Common",
        description="Showcase-only shared configuration.",
    )
    shared.set_string("app_name", "Acme SaaS Platform")
    shared.set_string("support_email", "support@acme.dev")
    shared.set_number("max_retries", 3)
    shared.set_number("request_timeout_ms", 5000)
    shared.set_number("pagination_default_page_size", 25)
    shared.set_number("max_retries", 5, environment="production")
    shared.set_number("request_timeout_ms", 10000, environment="production")
    shared.set_number("max_retries", 2, environment="staging")
    await shared.save()

    user_service = manage.config.new(
        "showcase-user-service",
        name="Showcase User Service",
        description="Configuration for the user microservice.",
        parent=shared,
    )
    user_service.set_string("database.host", "localhost")
    user_service.set_number("database.port", 5432)
    user_service.set_string("database.name", "users_dev")
    user_service.set_number("database.pool_size", 5)
    user_service.set_number("cache_ttl_seconds", 300)
    user_service.set_boolean("enable_signup", True)
    user_service.set_number("pagination_default_page_size", 50)
    user_service.set_string("database.host", "prod-users-rds.internal.acme.dev", environment="production")
    user_service.set_string("database.name", "users_prod", environment="production")
    user_service.set_number("database.pool_size", 20, environment="production")
    user_service.set_number("cache_ttl_seconds", 600, environment="production")
    user_service.set_boolean("enable_signup", False, environment="production")
    await user_service.save()

    auth_module = manage.config.new(
        "showcase-auth-module",
        name="Showcase Auth Module",
        description="Authentication module within the user service.",
        parent=shared,
    )
    auth_module.set_number("session_ttl_minutes", 60)
    auth_module.set_boolean("mfa_enabled", False)
    auth_module.set_number("session_ttl_minutes", 30, environment="production")
    auth_module.set_boolean("mfa_enabled", True, environment="production")
    await auth_module.save()


async def cleanup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
    for config_id in _DEMO_CONFIG_IDS:
        try:
            await manage.config.delete(config_id)
        except NotFoundError:
            pass
