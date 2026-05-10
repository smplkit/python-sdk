"""Smpl SDK Management — top-level :class:`SmplManagementClient` and namespaces.

The :class:`SmplManagementClient` (and its async variant) is the single
entry point for every management/CRUD operation in the SDK. It is the
counterpart to the runtime :class:`smplkit.SmplClient`, which is now
strictly for instrumentation: flag evaluation, config reads, log emission,
and audit-event recording.

Exposed namespaces:

- ``mgmt.contexts.*``
- ``mgmt.context_types.*``
- ``mgmt.environments.*``
- ``mgmt.account_settings.*``
- ``mgmt.config.*``
- ``mgmt.flags.*``
- ``mgmt.loggers.*``
- ``mgmt.log_groups.*``
- ``mgmt.audit.*``
"""

from __future__ import annotations

from smplkit.audit.models import ForwarderType
from smplkit.management.audit import (
    ActionListPage as AuditActionListPage,
    ActionsClient as AuditActionsClient,
    AsyncAuditClient as AsyncMgmtAuditClient,
    AuditClient as MgmtAuditClient,
    DeliveryListPage as AuditDeliveryListPage,
    EventListPage as AuditEventListPage,
    EventsClient as AuditEventsClient,
    ForwarderListPage as AuditForwarderListPage,
    ForwardersClient as AuditForwardersClient,
    ResourceTypeListPage as AuditResourceTypeListPage,
    ResourceTypesClient as AuditResourceTypesClient,
)
from smplkit.management.client import (
    AccountSettingsClient,
    AsyncAccountSettingsClient,
    AsyncConfigClient,
    AsyncContextsClient,
    AsyncContextTypesClient,
    AsyncEnvironmentsClient,
    AsyncFlagsClient,
    AsyncLogGroupsClient,
    AsyncLoggersClient,
    AsyncSmplManagementClient,
    ConfigClient,
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
    AsyncContextType,
    AsyncEnvironment,
    ContextType,
    Environment,
)
from smplkit.management.types import EnvironmentClassification

__all__ = [
    "AccountSettings",
    "AccountSettingsClient",
    "AsyncAccountSettings",
    "AsyncAccountSettingsClient",
    "AsyncConfigClient",
    "AsyncContextType",
    "AsyncContextTypesClient",
    "AsyncContextsClient",
    "AsyncEnvironment",
    "AsyncEnvironmentsClient",
    "AsyncFlagsClient",
    "AsyncLogGroupsClient",
    "AsyncLoggersClient",
    "AsyncMgmtAuditClient",
    "AsyncSmplManagementClient",
    "AuditActionListPage",
    "AuditActionsClient",
    "AuditDeliveryListPage",
    "AuditEventListPage",
    "AuditEventsClient",
    "AuditForwarderListPage",
    "AuditForwardersClient",
    "AuditResourceTypeListPage",
    "AuditResourceTypesClient",
    "ConfigClient",
    "ContextType",
    "ContextTypesClient",
    "ContextsClient",
    "Environment",
    "EnvironmentClassification",
    "EnvironmentsClient",
    "FlagsClient",
    "ForwarderType",
    "LogGroupsClient",
    "LoggersClient",
    "MgmtAuditClient",
    "SmplManagementClient",
]
