"""smplkit — Official Python SDK for the smplkit platform."""

from smplkit.client import AsyncSmplClient, SmplClient
from smplkit._errors import (
    ApiErrorDetail,
    SmplError,
    SmplConnectionError,
    SmplConflictError,
    SmplNotConnectedError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit.flags.types import Context, FlagType, Rule

__all__ = [
    "ApiErrorDetail",
    "AsyncSmplClient",
    "Context",
    "FlagType",
    "Rule",
    "SmplClient",
    "SmplError",
    "SmplConnectionError",
    "SmplConflictError",
    "SmplNotConnectedError",
    "SmplNotFoundError",
    "SmplTimeoutError",
    "SmplValidationError",
]

try:
    from smplkit._version import __version__
except ImportError:
    __version__ = "0.0.0"  # Fallback for editable installs without VCS
