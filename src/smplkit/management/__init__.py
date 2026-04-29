"""Smpl SDK Management — top-level :class:`SmplManagementClient` and namespaces.

The :class:`SmplManagementClient` (and its async variant) is the single
entry point for every management/CRUD operation in the SDK. It is the
counterpart to the runtime :class:`smplkit.SmplClient`, which is now
strictly for instrumentation: flag evaluation, config reads, log emission.

Exposed namespaces:

- ``mgmt.contexts.*``
- ``mgmt.context_types.*``
- ``mgmt.environments.*``
- ``mgmt.account_settings.*``
- ``mgmt.configs.*``
- ``mgmt.flags.*``
- ``mgmt.loggers.*``
- ``mgmt.log_groups.*``
"""

from __future__ import annotations

from smplkit.management.client import (
    AccountSettingsClient,
    AsyncAccountSettingsClient,
    AsyncConfigsClient,
    AsyncContextsClient,
    AsyncContextTypesClient,
    AsyncEnvironmentsClient,
    AsyncFlagsClient,
    AsyncLogGroupsClient,
    AsyncLoggersClient,
    AsyncSmplManagementClient,
    ConfigsClient,
    ContextsClient,
    ContextTypesClient,
    EnvironmentsClient,
    FlagsClient,
    LogGroupsClient,
    LoggersClient,
    SmplManagementClient,
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
    "AsyncConfigsClient",
    "AsyncContextEntity",
    "AsyncContextType",
    "AsyncContextTypesClient",
    "AsyncContextsClient",
    "AsyncEnvironment",
    "AsyncEnvironmentsClient",
    "AsyncFlagsClient",
    "AsyncLogGroupsClient",
    "AsyncLoggersClient",
    "AsyncSmplManagementClient",
    "ConfigsClient",
    "ContextEntity",
    "ContextType",
    "ContextTypesClient",
    "ContextsClient",
    "Environment",
    "EnvironmentClassification",
    "EnvironmentsClient",
    "FlagsClient",
    "LogGroupsClient",
    "LoggersClient",
    "SmplManagementClient",
]
