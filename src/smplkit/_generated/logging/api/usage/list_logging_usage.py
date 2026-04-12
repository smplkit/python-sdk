from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.usage_list_response import UsageListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filterperiod: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterperiod: None | str | Unset
    if isinstance(filterperiod, Unset):
        json_filterperiod = UNSET
    else:
        json_filterperiod = filterperiod
    params["filter[period]"] = json_filterperiod

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/usage",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | UsageListResponse | None:
    if response.status_code == 200:
        response_200 = UsageListResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ErrorResponse.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = ErrorResponse.from_dict(response.json())

        return response_401

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())

        return response_404

    if response.status_code == 429:
        response_429 = ErrorResponse.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorResponse | UsageListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterperiod: None | str | Unset = UNSET,
) -> Response[ErrorResponse | UsageListResponse]:
    """List Logging Usage

     Return current resource usage counts for the authenticated account.

    Args:
        filterperiod (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | UsageListResponse]
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
    filterperiod: None | str | Unset = UNSET,
) -> ErrorResponse | UsageListResponse | None:
    """List Logging Usage

     Return current resource usage counts for the authenticated account.

    Args:
        filterperiod (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | UsageListResponse
    """

    return sync_detailed(
        client=client,
        filterperiod=filterperiod,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterperiod: None | str | Unset = UNSET,
) -> Response[ErrorResponse | UsageListResponse]:
    """List Logging Usage

     Return current resource usage counts for the authenticated account.

    Args:
        filterperiod (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | UsageListResponse]
    """

    kwargs = _get_kwargs(
        filterperiod=filterperiod,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterperiod: None | str | Unset = UNSET,
) -> ErrorResponse | UsageListResponse | None:
    """List Logging Usage

     Return current resource usage counts for the authenticated account.

    Args:
        filterperiod (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | UsageListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterperiod=filterperiod,
        )
    ).parsed
