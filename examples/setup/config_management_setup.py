"""Setup / cleanup helpers for ``config_management_showcase.py``."""

from __future__ import annotations

from smplkit import NotFoundError

_DEMO_CONFIG_IDS = ["showcase-user-service", "showcase-common"]


# ``manage`` is a client.manage namespace (from SmplClient(...).manage).
async def setup_management_showcase(manage) -> None:
    await cleanup_management_showcase(manage)


async def cleanup_management_showcase(manage) -> None:
    for config_id in _DEMO_CONFIG_IDS:
        try:
            await manage.config.delete(config_id)
        except NotFoundError:
            pass
