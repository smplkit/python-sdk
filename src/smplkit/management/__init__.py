"""Smpl SDK management-plane CRUD sub-clients.

These back the ``client.manage`` namespace on the single
:class:`smplkit.SmplClient` — there is no separate management client class.
``client.manage`` exposes every CRUD/management operation:

- ``client.manage.contexts.*``
- ``client.manage.context_types.*``
- ``client.manage.environments.*``
- ``client.manage.services.*``
- ``client.manage.account_settings.*``

Config, flags, logging, audit, and jobs are the top-level ``client.config`` /
``client.flags`` / ``client.logging`` / ``client.audit`` / ``client.jobs``
(each a full client), not part of the management namespace. Logging CRUD lives
on ``client.logging.loggers`` / ``client.logging.log_groups``.
"""

from __future__ import annotations

from smplkit.audit.models import ForwarderType, TransformType
from smplkit.management.audit import (
    AsyncForwardersClient as AuditAsyncForwardersClient,
    ForwarderListPage as AuditForwarderListPage,
    ForwardersClient as AuditForwardersClient,
)
from smplkit.management._client import (
    AccountSettingsClient,
    AsyncAccountSettingsClient,
    AsyncContextsClient,
    AsyncContextTypesClient,
    AsyncEnvironmentsClient,
    AsyncServicesClient,
    ContextsClient,
    ContextTypesClient,
    EnvironmentsClient,
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
    "AsyncContextType",
    "AsyncContextTypesClient",
    "AsyncContextsClient",
    "AsyncEnvironment",
    "AsyncEnvironmentsClient",
    "AsyncService",
    "AsyncServicesClient",
    "AuditAsyncForwardersClient",
    "AuditForwarderListPage",
    "AuditForwardersClient",
    "ContextType",
    "ContextTypesClient",
    "ContextsClient",
    "Environment",
    "EnvironmentClassification",
    "EnvironmentsClient",
    "ForwarderType",
    "Service",
    "ServicesClient",
    "TransformType",
]
