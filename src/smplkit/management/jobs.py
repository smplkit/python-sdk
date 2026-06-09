"""Back-compat re-export for the Smpl Jobs models.

Smpl Jobs moved out of the management namespace into the top-level
:mod:`smplkit.jobs` package: Jobs installs no in-process machinery, so it has
no runtime/management split — it is a single client reachable as
``client.jobs``, ``mgmt.jobs``, or the standalone ``SmplJobsClient`` (see
:mod:`smplkit.jobs`).

This module survives only so existing imports of the shared jobs models —
e.g. ``from smplkit.management.jobs import HttpConfig`` — keep resolving.
Import from :mod:`smplkit.jobs` in new code.
"""

from smplkit.jobs.client import AsyncJob, HttpConfig, Job, Run, Usage

__all__ = ["HttpConfig", "Job", "AsyncJob", "Run", "Usage"]
