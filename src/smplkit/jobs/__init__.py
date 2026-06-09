"""Smpl Jobs SDK namespace.

Smpl Jobs schedules HTTP calls (cron-style ``schedule`` + ``http``
configuration) and records their run history. Unlike Config/Flags/Logging it
installs no in-process machinery, so it has no runtime/management split: a
single :class:`SmplJobsClient` (sync) / :class:`AsyncSmplJobsClient` (async)
exposes the full surface and is reachable as ``client.jobs`` on
:class:`smplkit.SmplClient` or constructed directly via
:class:`SmplJobsClient`.

The shared dataclasses (:class:`Job`, :class:`AsyncJob`, :class:`Run`,
:class:`Usage`, :class:`HttpConfig`) live in :mod:`smplkit.jobs.client` and are
re-exported here.
"""

from smplkit.jobs.client import (
    AsyncJob,
    AsyncSmplJobsClient,
    HttpConfig,
    Job,
    Run,
    SmplJobsClient,
    Usage,
)

__all__ = [
    "AsyncJob",
    "AsyncSmplJobsClient",
    "HttpConfig",
    "Job",
    "Run",
    "SmplJobsClient",
    "Usage",
]
