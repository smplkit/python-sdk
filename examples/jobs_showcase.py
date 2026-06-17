"""
Demonstrates the smplkit management SDK for Smpl Jobs.

A job is enabled per environment: a recurring job carries an ``environments``
map (each entry an enablement flag plus an optional per-environment request
override), while a one-off job is born in a single environment. Every run is
stamped with the environment it executed in, and run history can be filtered by
environment. This showcase walks through both.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/jobs_showcase.py
"""

import asyncio
import uuid

from smplkit import AsyncJobsClient, NotFoundError
from smplkit.jobs import HttpConfig, JobEnvironment


async def main() -> None:

    # Jobs has no runtime/management split — one client. Here we use the
    # standalone AsyncJobsClient (use JobsClient for synchronous use); the same
    # surface is also reachable as ``client.jobs`` on a SmplClient. The
    # configured environment is the default for run history and the environment
    # a one-off job is born in.
    async with AsyncJobsClient(environment="production") as jobs:
        job_id = f"showcase-mgmt-{uuid.uuid4().hex[:8]}"
        oneoff_id = f"showcase-oneoff-{uuid.uuid4().hex[:8]}"

        try:
            # create a recurring job enabled in production, with a development
            # override that posts to a different URL
            job = jobs.new(
                job_id,
                name="Nightly cache warm",
                description="Warms the product cache every night at 02:00 UTC.",
                schedule="0 2 * * *",  # 5-field cron, UTC -> recurring
                configuration=HttpConfig(
                    method="POST",
                    url="https://api.example.com/cache/warm",
                    headers=[("Authorization", "Bearer s3cr3t")],
                    body='{"scope": "all"}',
                    timeout=30,
                ),
                environments={
                    "production": JobEnvironment(enabled=True),
                    "development": JobEnvironment(
                        enabled=False,
                        configuration=HttpConfig(
                            method="POST",
                            url="https://development.example.com/cache/warm",
                            headers=[("Authorization", "Bearer development-s3cr3t")],
                            body='{"scope": "all"}',
                        ),
                    ),
                },
            )
            await job.save()
            assert job.version == 1
            enabled_in = sorted(k for k, v in job.environments.items() if v.enabled)
            print(f"Created recurring job {job.id!r} (v{job.version}) enabled in {enabled_in}")

            # get a job: 'enabled' is a read-only roll-up (enabled in >= 1 env),
            # and each environment's override round-trips
            fetched = await jobs.get(job_id)
            assert fetched.enabled is True
            assert fetched.environments["development"].configuration.url == "https://development.example.com/cache/warm"
            print(f"Fetched job {job_id!r} (enabled={fetched.enabled})")

            # list jobs (filter by the derived 'enabled' roll-up)
            listing = await jobs.list(enabled=True)
            assert job_id in {j.id for j in listing}
            print(f"Found job {job_id!r} in the enabled listing")

            # update: rename, reschedule, and turn on development too
            job.name = "Nightly cache warm (v2)"
            job.schedule = "30 2 * * *"
            job.set_enabled(True, environment="development")
            await job.save()
            assert job.version == 2 and job.environments["development"].enabled is True
            print(f"Updated job to v{job.version}: now enabled in production and development")

            # trigger an immediate run (a MANUAL run) in production
            run = await jobs.run(job_id, environment="production")
            assert run.trigger == "MANUAL" and run.environment == "production"
            print(f"Triggered run {run.id} (trigger={run.trigger}, env={run.environment})")

            # read this job's production run history, and fetch a single run
            runs = await jobs.runs.list(job=job_id, environments=["production"])
            assert any(r.id == run.id for r in runs)
            got = await jobs.runs.get(run.id)
            assert got.environment == "production"
            print(f"Listed {len(runs)} production run(s); fetched run {got.id} (env={got.environment})")

            # re-run from a prior run (inherits its environment), then cancel it
            rerun = await jobs.runs.rerun(run.id)
            assert rerun.trigger == "RERUN" and rerun.environment == run.environment
            canceled = await jobs.runs.cancel(rerun.id)
            assert canceled.status == "CANCELED"
            print(f"Re-ran ({rerun.id}, env={rerun.environment}) then canceled it -> {canceled.status}")

            # create a one-off job born in development (single-shot; no environments map)
            oneoff = jobs.new(
                oneoff_id,
                name="One-shot reindex",
                schedule="now",  # one-off -> born in the named environment
                configuration=HttpConfig(method="POST", url="https://api.example.com/reindex"),
                environment="development",
            )
            await oneoff.save()
            assert oneoff.version == 1 and oneoff.environments["development"].enabled is True
            print(f"Created one-off job {oneoff.id!r} born in development")

            # delete a job
            await job.delete()
            assert job_id not in {j.id for j in await jobs.list()}
            print(f"Deleted job {job_id!r} — jobs showcase complete.")
        finally:
            # tear-down: never leave a showcase job behind, even on failure
            for stale in (job_id, oneoff_id):
                try:
                    await jobs.delete(stale)
                except NotFoundError:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
