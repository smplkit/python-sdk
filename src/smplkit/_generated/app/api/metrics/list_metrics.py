from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.metric_list_response import MetricListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filtername: str,
    filterrecorded_at: Union[None, Unset, str] = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["filter[name]"] = filtername

    json_filterrecorded_at: Union[None, Unset, str]
    if isinstance(filterrecorded_at, Unset):
        json_filterrecorded_at = UNSET
    else:
        json_filterrecorded_at = filterrecorded_at
    params["filter[recorded_at]"] = json_filterrecorded_at

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/metrics",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorResponse, MetricListResponse]]:
    if response.status_code == 200:
        response_200 = MetricListResponse.from_dict(response.json())

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
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorResponse, MetricListResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filtername: str,
    filterrecorded_at: Union[None, Unset, str] = UNSET,
) -> Response[Union[ErrorResponse, MetricListResponse]]:
    """List Metrics

    Args:
        filtername (str):
        filterrecorded_at (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, MetricListResponse]]
    """

    kwargs = _get_kwargs(
        filtername=filtername,
        filterrecorded_at=filterrecorded_at,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtername: str,
    filterrecorded_at: Union[None, Unset, str] = UNSET,
) -> Optional[Union[ErrorResponse, MetricListResponse]]:
    """List Metrics

    Args:
        filtername (str):
        filterrecorded_at (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, MetricListResponse]
    """

    return sync_detailed(
        client=client,
        filtername=filtername,
        filterrecorded_at=filterrecorded_at,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtername: str,
    filterrecorded_at: Union[None, Unset, str] = UNSET,
) -> Response[Union[ErrorResponse, MetricListResponse]]:
    """List Metrics

    Args:
        filtername (str):
        filterrecorded_at (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, MetricListResponse]]
    """

    kwargs = _get_kwargs(
        filtername=filtername,
        filterrecorded_at=filterrecorded_at,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtername: str,
    filterrecorded_at: Union[None, Unset, str] = UNSET,
) -> Optional[Union[ErrorResponse, MetricListResponse]]:
    """List Metrics

    Args:
        filtername (str):
        filterrecorded_at (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, MetricListResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            filtername=filtername,
            filterrecorded_at=filterrecorded_at,
        )
    ).parsed
