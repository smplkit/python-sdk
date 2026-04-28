"""Shared types for ``client.management.*``."""

from __future__ import annotations

import enum


class EnvironmentClassification(str, enum.Enum):
    """Whether an environment participates in the canonical ordering.

    STANDARD environments are the customer's deploy targets — production,
    staging, development, etc. They participate in
    ``account_settings.environment_order`` and appear in the standard
    Console environment columns.

    AD_HOC environments are transient targets (preview branches,
    individual developer sandboxes) that should not appear in the
    standard ordering.
    """

    STANDARD = "STANDARD"
    AD_HOC = "AD_HOC"
