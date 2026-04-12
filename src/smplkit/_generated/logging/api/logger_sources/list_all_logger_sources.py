from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.logger_source_list_response import LoggerSourceListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filterenvironment: None | str | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterenvironment: None | str | Unset
    if isinstance(filterenvironment, Unset):
        json_filterenvironment = UNSET
    else:
        json_filterenvironment = filterenvironment
    params["filter[environment]"] = json_filterenvironment

    json_filterservice: None | str | Unset
    if isinstance(filterservice, Unset):
        json_filterservice = UNSET
    else:
        json_filterservice = filterservice
    params["filter[service]"] = json_filterservice

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/logger_sources",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | LoggerSourceListResponse | None:
    if response.status_code == 200:
        response_200 = LoggerSourceListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | LoggerSourceListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
) -> Response[ErrorResponse | LoggerSourceListResponse]:
    """List All Logger Sources

     List all logger sources across all loggers. Optionally filter by environment or service.

    Args:
        filterenvironment (None | str | Unset):
        filterservice (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | LoggerSourceListResponse]
    """

    kwargs = _get_kwargs(
        filterenvironment=filterenvironment,
        filterservice=filterservice,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
) -> ErrorResponse | LoggerSourceListResponse | None:
    """List All Logger Sources

     List all logger sources across all loggers. Optionally filter by environment or service.

    Args:
        filterenvironment (None | str | Unset):
        filterservice (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | LoggerSourceListResponse
    """

    return sync_detailed(
        client=client,
        filterenvironment=filterenvironment,
        filterservice=filterservice,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
) -> Response[ErrorResponse | LoggerSourceListResponse]:
    """List All Logger Sources

     List all logger sources across all loggers. Optionally filter by environment or service.

    Args:
        filterenvironment (None | str | Unset):
        filterservice (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | LoggerSourceListResponse]
    """

    kwargs = _get_kwargs(
        filterenvironment=filterenvironment,
        filterservice=filterservice,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
) -> ErrorResponse | LoggerSourceListResponse | None:
    """List All Logger Sources

     List all logger sources across all loggers. Optionally filter by environment or service.

    Args:
        filterenvironment (None | str | Unset):
        filterservice (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | LoggerSourceListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterenvironment=filterenvironment,
            filterservice=filterservice,
        )
    ).parsed
