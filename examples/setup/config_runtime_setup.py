"""Setup and simulation helpers for ``config_runtime_showcase.py``.

The runtime showcase is intentionally runtime-only — declarations,
typed getters, change listeners. In a real deployment the configs
would either already exist (admin-curated) or be created by the
SDK's discovery on first run. Here we pre-create them through the
management API so the showcase can also demonstrate a live admin
override end-to-end in a single process.
"""

from __future__ import annotations

from smplkit._errors import NotFoundError
from smplkit.management.client import AsyncSmplManagementClient

_DEMO_CONFIG_IDS = ["showcase-billing", "showcase-common"]


async def setup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
    await cleanup_runtime_showcase(manage)

    common = manage.config.new("showcase-common", description="Shared defaults for showcase services.")
    common.set_string("app.name", "Acme SaaS")
    common.set_string("support.email", "support@acme.dev")
    await common.save()

    billing = manage.config.new(
        "showcase-billing",
        description="Plan-limit configuration for billing.",
        parent="showcase-common",
    )
    billing.set_number("plan.max_seats", 5, description="Maximum seats per organization.")
    billing.set_number("plan.trial_days", 14)
    billing.set_string("plan.tier", "free")
    await billing.save()


async def simulate_admin_override(manage: AsyncSmplManagementClient) -> None:
    """Apply a per-environment override on ``showcase-billing.plan.max_seats``."""
    billing = await manage.config.get("showcase-billing")
    billing.set_number("plan.max_seats", 25, environment="production")
    await billing.save()


async def cleanup_runtime_showcase(manage: AsyncSmplManagementClient) -> None:
    for config_id in _DEMO_CONFIG_IDS:
        try:
            await manage.config.delete(config_id)
        except NotFoundError:
            pass
