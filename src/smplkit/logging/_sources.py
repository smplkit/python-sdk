"""LoggerSource — explicit logger registration descriptor."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smplkit import LogLevel


@dataclasses.dataclass
class LoggerSource:
    """Describes a logger to register via :meth:`LoggingManagementClient.register_sources`.

    Unlike auto-discovery (which reads the current process's logging framework),
    ``register_sources`` accepts explicit ``(service, environment)`` overrides —
    useful for sample-data seeding, cross-tenant migration, and test fixtures.

    Args:
        name: Logger name (e.g. ``"sqlalchemy.engine"``).  Normalized to lowercase
            with slashes and colons replaced by dots before sending to the API.
        service: Service name this source belongs to.
        environment: Environment name this source belongs to.
        resolved_level: Effective log level for this source.
        level: Explicit (configured) log level, if different from ``resolved_level``.
            Pass ``None`` when the level is inherited.
    """

    name: str
    service: str
    environment: str
    resolved_level: LogLevel
    level: LogLevel | None = None
