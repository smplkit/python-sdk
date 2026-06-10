"""Back-compat shims for the former management namespace.

The ``client.manage`` namespace was split into ``client.platform`` (environment
/ service / context / context-type CRUD) and ``client.account`` (account
settings). The cross-cutting CRUD sub-clients now live in
:mod:`smplkit.platform` and :mod:`smplkit.account`; the SIEM forwarder client
lives in :mod:`smplkit.management.audit`, and the Smpl Jobs models in
:mod:`smplkit.management.jobs`.

This package survives only to keep a handful of historical import paths
(models, types, the audit forwarder client) resolving. New code should import
from :mod:`smplkit` (clients), :mod:`smplkit.platform`, or :mod:`smplkit.account`.
"""

from __future__ import annotations

from smplkit.account.models import AccountSettings, AsyncAccountSettings
from smplkit.audit.models import ForwarderType, TransformType
from smplkit.management.audit import (
    AsyncForwardersClient as AuditAsyncForwardersClient,
    ForwarderListPage as AuditForwarderListPage,
    ForwardersClient as AuditForwardersClient,
)
from smplkit.platform.models import (
    AsyncContextType,
    AsyncEnvironment,
    AsyncService,
    ContextType,
    Environment,
    Service,
)
from smplkit.platform.types import Color, EnvironmentClassification

__all__ = [
    "AccountSettings",
    "AsyncAccountSettings",
    "AsyncContextType",
    "AsyncEnvironment",
    "AsyncService",
    "AuditAsyncForwardersClient",
    "AuditForwarderListPage",
    "AuditForwardersClient",
    "Color",
    "ContextType",
    "Environment",
    "EnvironmentClassification",
    "ForwarderType",
    "Service",
    "TransformType",
]
