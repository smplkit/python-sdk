"""Smpl Flags SDK module — wraps generated flags client."""

from smplkit.flags.client import (
    AsyncFlagsClient,
    AsyncFlagsManagementClient,
    FlagChangeEvent,
    FlagsClient,
    FlagsManagementClient,
    FlagStats,
)
from smplkit.flags.models import (
    AsyncBooleanFlag,
    AsyncFlag,
    AsyncJsonFlag,
    AsyncNumberFlag,
    AsyncStringFlag,
    BooleanFlag,
    Flag,
    JsonFlag,
    NumberFlag,
    StringFlag,
)
from smplkit.flags.types import Context, Rule

__all__ = [
    "AsyncBooleanFlag",
    "AsyncFlag",
    "AsyncFlagsClient",
    "AsyncFlagsManagementClient",
    "AsyncJsonFlag",
    "AsyncNumberFlag",
    "AsyncStringFlag",
    "BooleanFlag",
    "Context",
    "Flag",
    "FlagChangeEvent",
    "FlagsClient",
    "FlagsManagementClient",
    "FlagStats",
    "JsonFlag",
    "NumberFlag",
    "Rule",
    "StringFlag",
]
