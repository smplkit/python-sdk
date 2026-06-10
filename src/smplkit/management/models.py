"""Back-compat re-export for the platform / account active-record models.

The cross-cutting models moved to :mod:`smplkit.platform.models` (Environment,
Service, ContextType and async variants) and :mod:`smplkit.account.models`
(AccountSettings) when the management namespace was split into
``client.platform`` / ``client.account``. This module survives so existing
imports — e.g. ``from smplkit.management.models import Environment`` — keep
resolving. Import from :mod:`smplkit.platform` / :mod:`smplkit.account` in new
code.
"""

from smplkit.account.models import AccountSettings, AsyncAccountSettings
from smplkit.platform.models import (
    AsyncContextType,
    AsyncEnvironment,
    AsyncService,
    ContextType,
    Environment,
    Service,
)

__all__ = [
    "AccountSettings",
    "AsyncAccountSettings",
    "AsyncContextType",
    "AsyncEnvironment",
    "AsyncService",
    "ContextType",
    "Environment",
    "Service",
]
