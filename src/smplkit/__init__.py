"""smplkit — Official Python SDK for the smplkit platform."""

import enum

from smplkit.client import AsyncSmplClient, SmplClient
from smplkit._errors import (
    ApiErrorDetail,
    Error,
    ConnectionError,
    ConflictError,
    NotFoundError,
    TimeoutError,
    ValidationError,
)
from smplkit.config.models import ConfigEnvironment, ConfigItem, ItemType
from smplkit.flags.models import FlagEnvironment, FlagRule, FlagValue
from smplkit.flags.types import Context, FlagDeclaration, Op, Rule
from smplkit.logging._sources import LoggerSource
from smplkit.management.client import AsyncSmplManagementClient, SmplManagementClient
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
    "AsyncSmplManagementClient",
    "ConfigEnvironment",
    "ConfigItem",
    "Context",
    "EnvironmentClassification",
    "FlagDeclaration",
    "FlagEnvironment",
    "FlagRule",
    "FlagValue",
    "ItemType",
    "LoggerSource",
    "LogLevel",
    "Op",
    "Rule",
    "SmplClient",
    "Error",
    "ConnectionError",
    "ConflictError",
    "SmplManagementClient",
    "NotFoundError",
    "TimeoutError",
    "ValidationError",
]

try:
    from smplkit._version import __version__
except ImportError:
    __version__ = "0.0.0"  # Fallback for editable installs without VCS
