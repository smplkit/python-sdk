from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.usage_response import UsageResponse


def _get_kwargs(
    *,
    filterperiod: str,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["filter[period]"] = filterperiod

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/usage",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> UsageResponse | None:
    if response.status_code == 200:
        response_200 = UsageResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[UsageResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterperiod: str,
) -> Response[UsageResponse]:
    """List Usage

     Report the current-period usage counters for this account.

    Args:
        filterperiod (str): Period to report. `current` is the only supported value.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UsageResponse]
    """

    kwargs = _get_kwargs(
        filterperiod=filterperiod,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterperiod: str,
) -> UsageResponse | None:
    """List Usage

     Report the current-period usage counters for this account.

    Args:
        filterperiod (str): Period to report. `current` is the only supported value.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UsageResponse
    """

    return sync_detailed(
        client=client,
        filterperiod=filterperiod,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterperiod: str,
) -> Response[UsageResponse]:
    """List Usage

     Report the current-period usage counters for this account.

    Args:
        filterperiod (str): Period to report. `current` is the only supported value.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UsageResponse]
    """

    kwargs = _get_kwargs(
        filterperiod=filterperiod,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterperiod: str,
) -> UsageResponse | None:
    """List Usage

     Report the current-period usage counters for this account.

    Args:
        filterperiod (str): Period to report. `current` is the only supported value.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UsageResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterperiod=filterperiod,
        )
    ).parsed
