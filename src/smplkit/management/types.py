"""Back-compat re-export for the platform shared types.

The cross-cutting platform types moved to :mod:`smplkit.platform.types` when
the management namespace was split into ``client.platform`` / ``client.account``.
This module survives so existing imports — e.g.
``from smplkit.management.types import Color`` — keep resolving. Import from
:mod:`smplkit.platform` in new code.
"""

from smplkit.platform.types import Color, EnvironmentClassification

__all__ = ["Color", "EnvironmentClassification"]
