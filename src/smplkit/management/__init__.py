"""Smpl SDK Management — wraps generated app client.

The ``client.management.*`` namespace covers app-service-owned
resources that aren't tied to a specific microservice: environments,
contexts, context types, and per-account settings.
"""

from __future__ import annotations

from smplkit.management.client import (
    AsyncAccountSettingsClient,
    AsyncContextsClient,
    AsyncContextTypesClient,
    AsyncEnvironmentsClient,
    AsyncManagementClient,
    AccountSettingsClient,
    ContextsClient,
    ContextTypesClient,
    EnvironmentsClient,
    ManagementClient,
)
from smplkit.management.models import (
    AccountSettings,
    AsyncAccountSettings,
    AsyncContextEntity,
    AsyncContextType,
    AsyncEnvironment,
    ContextEntity,
    ContextType,
    Environment,
)
from smplkit.management.types import EnvironmentClassification

__all__ = [
    "AccountSettings",
    "AccountSettingsClient",
    "AsyncAccountSettings",
    "AsyncAccountSettingsClient",
    "AsyncContextEntity",
    "AsyncContextType",
    "AsyncContextTypesClient",
    "AsyncContextsClient",
    "AsyncEnvironment",
    "AsyncEnvironmentsClient",
    "AsyncManagementClient",
    "ContextEntity",
    "ContextType",
    "ContextTypesClient",
    "ContextsClient",
    "Environment",
    "EnvironmentClassification",
    "EnvironmentsClient",
    "ManagementClient",
]
