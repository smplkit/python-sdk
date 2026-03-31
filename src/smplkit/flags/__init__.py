"""Smpl Flags SDK module — wraps generated flags client."""

from smplkit.flags.client import (
    AsyncFlagsClient,
    BoolFlagHandle,
    FlagChangeEvent,
    FlagsClient,
    FlagStats,
    JsonFlagHandle,
    NumberFlagHandle,
    StringFlagHandle,
)
from smplkit.flags.models import AsyncFlag, ContextType, Flag
from smplkit.flags.types import Context, FlagType, Rule

__all__ = [
    "AsyncFlag",
    "AsyncFlagsClient",
    "BoolFlagHandle",
    "Context",
    "ContextType",
    "Flag",
    "FlagChangeEvent",
    "FlagsClient",
    "FlagStats",
    "FlagType",
    "JsonFlagHandle",
    "NumberFlagHandle",
    "Rule",
    "StringFlagHandle",
]
