"""smplkit — Official Python SDK for the smplkit platform."""

import enum

from smplkit.client import AsyncSmplClient, SmplClient
from smplkit._errors import (
    ApiErrorDetail,
    SmplError,
    SmplConnectionError,
    SmplConflictError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit.flags.types import Context, Rule
from smplkit.logging._sources import LoggerSource
from smplkit.management.types import EnvironmentClassification


class LogLevel(str, enum.Enum):
    """Log severity levels used by the Smpl Logging service."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"
    SILENT = "SILENT"


__all__ = [
    "ApiErrorDetail",
    "AsyncSmplClient",
    "Context",
    "EnvironmentClassification",
    "LoggerSource",
    "LogLevel",
    "Rule",
    "SmplClient",
    "SmplError",
    "SmplConnectionError",
    "SmplConflictError",
    "SmplNotFoundError",
    "SmplTimeoutError",
    "SmplValidationError",
]

try:
    from smplkit._version import __version__
except ImportError:
    __version__ = "0.0.0"  # Fallback for editable installs without VCS
