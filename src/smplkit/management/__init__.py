"""Smpl SDK management-plane CRUD sub-clients.

These back the ``client.manage`` namespace on the single
:class:`smplkit.SmplClient` — there is no separate management client class.
``client.manage`` exposes every CRUD/management operation:

- ``client.manage.contexts.*``
- ``client.manage.context_types.*``
- ``client.manage.environments.*``
- ``client.manage.services.*``
- ``client.manage.account_settings.*``
- ``client.manage.config.*``
- ``client.manage.flags.*``
- ``client.manage.loggers.*``
- ``client.manage.log_groups.*``

Audit and jobs are the top-level ``client.audit`` / ``client.jobs`` (each a
full client), not part of the management namespace.
"""

from __future__ import annotations

from smplkit.audit.models import ForwarderType, TransformType
from smplkit.management.audit import (
    AsyncForwardersClient as AuditAsyncForwardersClient,
    ForwarderListPage as AuditForwarderListPage,
    ForwardersClient as AuditForwardersClient,
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
    AsyncServicesClient,
    ConfigClient,
    ContextsClient,
    ContextTypesClient,
    EnvironmentsClient,
    FlagsClient,
    LogGroupsClient,
    LoggersClient,
    ServicesClient,
)
from smplkit.management.models import (
    AccountSettings,
    AsyncAccountSettings,
    AsyncContextType,
    AsyncEnvironment,
    AsyncService,
    ContextType,
    Environment,
    Service,
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
    "AsyncService",
    "AsyncServicesClient",
    "AuditAsyncForwardersClient",
    "AuditForwarderListPage",
    "AuditForwardersClient",
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
    "Service",
    "ServicesClient",
    "TransformType",
]
