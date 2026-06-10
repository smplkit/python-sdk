"""Smpl Logging SDK module — wraps generated logging client.

``LoggingClient`` / ``AsyncLoggingClient`` are re-exported from the top-level
``smplkit`` package only (alongside ``ConfigClient`` / ``FlagsClient``), not
from here.
"""

from __future__ import annotations

from smplkit.logging._sources import LoggerSource
from smplkit.logging.adapters.base import LoggingAdapter
from smplkit.logging.adapters.stdlib_logging import StdlibLoggingAdapter
from smplkit.logging.models import (
    AsyncSmplLogGroup,
    AsyncSmplLogger,
    SmplLogGroup,
    SmplLogger,
)

__all__ = [
    "AsyncSmplLogGroup",
    "AsyncSmplLogger",
    "LoggerSource",
    "LoggingAdapter",
    "SmplLogGroup",
    "SmplLogger",
    "StdlibLoggingAdapter",
]
