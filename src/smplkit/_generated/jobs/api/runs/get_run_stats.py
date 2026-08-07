from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_run_stats_bucket_type_0 import GetRunStatsBucketType0
from ...models.run_stats_response import RunStatsResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    filtercreated_at: None | str | Unset = UNSET,
    filterenvironment: None | str | Unset = UNSET,
    bucket: GetRunStatsBucketType0 | None | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filtercreated_at: str | Unset | None
    if isinstance(filtercreated_at, Unset):
        json_filtercreated_at = UNSET
    else:
        json_filtercreated_at = filtercreated_at
    params["filter[created_at]"] = json_filtercreated_at

    json_filterenvironment: str | Unset | None
    if isinstance(filterenvironment, Unset):
        json_filterenvironment = UNSET
    else:
        json_filterenvironment = filterenvironment
    params["filter[environment]"] = json_filterenvironment

    json_bucket: str | Unset | None
    if isinstance(bucket, Unset):
        json_bucket = UNSET
    elif isinstance(bucket, str):
        json_bucket = bucket
    else:
        json_bucket = bucket
    params["bucket"] = json_bucket

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/run_stats",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> RunStatsResponse | None:
    if response.status_code == 200:
        response_200 = RunStatsResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[RunStatsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filtercreated_at: None | str | Unset = UNSET,
    filterenvironment: None | str | Unset = UNSET,
    bucket: GetRunStatsBucketType0 | None | Unset = UNSET,
) -> Response[RunStatsResponse]:
    """Get Run Stats

     Report aggregated statistics over this account's runs.

    One request answers the common monitoring questions: how many runs matched
    the filters (`total`), how they broke down by lifecycle state (`tally`),
    how they were distributed over time (`buckets`, when the `bucket`
    directive is given), which runs failed most recently (`recent_failures`,
    at most 3, newest first), and what fires next (`next_scheduled`).

    Filters compose with AND:

    - `filter[created_at]` — a half-open `[start,end)` date range (see the
      parameter for the interval syntax).
    - `filter[environment]` — one environment key or a comma-separated list
      (any-of); omitted covers every environment you can access.

    `next_scheduled` honors only the environment filter: it reports the
    soonest `PENDING` run with a fire time at or after the request, no matter
    when that run was created.

    The resource id is always `current` — statistics are computed at read
    time, not stored.

    Args:
        filtercreated_at (None | str | Unset): Restrict the statistics to runs whose `created_at`
            falls in a half-open `[start,end)` interval. Bounds are ISO-8601 timestamps; `*` leaves a
            bound open. The leading bracket is `[` (inclusive) or `(` (exclusive) and the trailing
            bracket is `]` (inclusive) or `)` (exclusive). Example: `[2026-06-01T00:00:00Z,*)` covers
            everything from June 1 onward. Does not apply to `next_scheduled`.
        filterenvironment (None | str | Unset): Comma-separated list of environment keys to scope
            the statistics to (e.g. `production,staging`). When omitted, statistics cover every
            environment you can access.
        bucket (GetRunStatsBucketType0 | None | Unset): Also return run counts over time, grouped
            into buckets of this size (a directive, not a filter). One of `1m`, `5m`, `15m`, `1h`,
            `6h`, or `1d`. Omit to skip the time series.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[RunStatsResponse]
    """

    kwargs = _get_kwargs(
        filtercreated_at=filtercreated_at,
        filterenvironment=filterenvironment,
        bucket=bucket,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtercreated_at: None | str | Unset = UNSET,
    filterenvironment: None | str | Unset = UNSET,
    bucket: GetRunStatsBucketType0 | None | Unset = UNSET,
) -> RunStatsResponse | None:
    """Get Run Stats

     Report aggregated statistics over this account's runs.

    One request answers the common monitoring questions: how many runs matched
    the filters (`total`), how they broke down by lifecycle state (`tally`),
    how they were distributed over time (`buckets`, when the `bucket`
    directive is given), which runs failed most recently (`recent_failures`,
    at most 3, newest first), and what fires next (`next_scheduled`).

    Filters compose with AND:

    - `filter[created_at]` — a half-open `[start,end)` date range (see the
      parameter for the interval syntax).
    - `filter[environment]` — one environment key or a comma-separated list
      (any-of); omitted covers every environment you can access.

    `next_scheduled` honors only the environment filter: it reports the
    soonest `PENDING` run with a fire time at or after the request, no matter
    when that run was created.

    The resource id is always `current` — statistics are computed at read
    time, not stored.

    Args:
        filtercreated_at (None | str | Unset): Restrict the statistics to runs whose `created_at`
            falls in a half-open `[start,end)` interval. Bounds are ISO-8601 timestamps; `*` leaves a
            bound open. The leading bracket is `[` (inclusive) or `(` (exclusive) and the trailing
            bracket is `]` (inclusive) or `)` (exclusive). Example: `[2026-06-01T00:00:00Z,*)` covers
            everything from June 1 onward. Does not apply to `next_scheduled`.
        filterenvironment (None | str | Unset): Comma-separated list of environment keys to scope
            the statistics to (e.g. `production,staging`). When omitted, statistics cover every
            environment you can access.
        bucket (GetRunStatsBucketType0 | None | Unset): Also return run counts over time, grouped
            into buckets of this size (a directive, not a filter). One of `1m`, `5m`, `15m`, `1h`,
            `6h`, or `1d`. Omit to skip the time series.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        RunStatsResponse
    """

    return sync_detailed(
        client=client,
        filtercreated_at=filtercreated_at,
        filterenvironment=filterenvironment,
        bucket=bucket,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtercreated_at: None | str | Unset = UNSET,
    filterenvironment: None | str | Unset = UNSET,
    bucket: GetRunStatsBucketType0 | None | Unset = UNSET,
) -> Response[RunStatsResponse]:
    """Get Run Stats

     Report aggregated statistics over this account's runs.

    One request answers the common monitoring questions: how many runs matched
    the filters (`total`), how they broke down by lifecycle state (`tally`),
    how they were distributed over time (`buckets`, when the `bucket`
    directive is given), which runs failed most recently (`recent_failures`,
    at most 3, newest first), and what fires next (`next_scheduled`).

    Filters compose with AND:

    - `filter[created_at]` — a half-open `[start,end)` date range (see the
      parameter for the interval syntax).
    - `filter[environment]` — one environment key or a comma-separated list
      (any-of); omitted covers every environment you can access.

    `next_scheduled` honors only the environment filter: it reports the
    soonest `PENDING` run with a fire time at or after the request, no matter
    when that run was created.

    The resource id is always `current` — statistics are computed at read
    time, not stored.

    Args:
        filtercreated_at (None | str | Unset): Restrict the statistics to runs whose `created_at`
            falls in a half-open `[start,end)` interval. Bounds are ISO-8601 timestamps; `*` leaves a
            bound open. The leading bracket is `[` (inclusive) or `(` (exclusive) and the trailing
            bracket is `]` (inclusive) or `)` (exclusive). Example: `[2026-06-01T00:00:00Z,*)` covers
            everything from June 1 onward. Does not apply to `next_scheduled`.
        filterenvironment (None | str | Unset): Comma-separated list of environment keys to scope
            the statistics to (e.g. `production,staging`). When omitted, statistics cover every
            environment you can access.
        bucket (GetRunStatsBucketType0 | None | Unset): Also return run counts over time, grouped
            into buckets of this size (a directive, not a filter). One of `1m`, `5m`, `15m`, `1h`,
            `6h`, or `1d`. Omit to skip the time series.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[RunStatsResponse]
    """

    kwargs = _get_kwargs(
        filtercreated_at=filtercreated_at,
        filterenvironment=filterenvironment,
        bucket=bucket,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtercreated_at: None | str | Unset = UNSET,
    filterenvironment: None | str | Unset = UNSET,
    bucket: GetRunStatsBucketType0 | None | Unset = UNSET,
) -> RunStatsResponse | None:
    """Get Run Stats

     Report aggregated statistics over this account's runs.

    One request answers the common monitoring questions: how many runs matched
    the filters (`total`), how they broke down by lifecycle state (`tally`),
    how they were distributed over time (`buckets`, when the `bucket`
    directive is given), which runs failed most recently (`recent_failures`,
    at most 3, newest first), and what fires next (`next_scheduled`).

    Filters compose with AND:

    - `filter[created_at]` — a half-open `[start,end)` date range (see the
      parameter for the interval syntax).
    - `filter[environment]` — one environment key or a comma-separated list
      (any-of); omitted covers every environment you can access.

    `next_scheduled` honors only the environment filter: it reports the
    soonest `PENDING` run with a fire time at or after the request, no matter
    when that run was created.

    The resource id is always `current` — statistics are computed at read
    time, not stored.

    Args:
        filtercreated_at (None | str | Unset): Restrict the statistics to runs whose `created_at`
            falls in a half-open `[start,end)` interval. Bounds are ISO-8601 timestamps; `*` leaves a
            bound open. The leading bracket is `[` (inclusive) or `(` (exclusive) and the trailing
            bracket is `]` (inclusive) or `)` (exclusive). Example: `[2026-06-01T00:00:00Z,*)` covers
            everything from June 1 onward. Does not apply to `next_scheduled`.
        filterenvironment (None | str | Unset): Comma-separated list of environment keys to scope
            the statistics to (e.g. `production,staging`). When omitted, statistics cover every
            environment you can access.
        bucket (GetRunStatsBucketType0 | None | Unset): Also return run counts over time, grouped
            into buckets of this size (a directive, not a filter). One of `1m`, `5m`, `15m`, `1h`,
            `6h`, or `1d`. Omit to skip the time series.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        RunStatsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filtercreated_at=filtercreated_at,
            filterenvironment=filterenvironment,
            bucket=bucket,
        )
    ).parsed
