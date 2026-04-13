from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.logger_list_response import LoggerListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filtermanaged: bool | None | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
    filterlast_seen: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filtermanaged: bool | None | Unset
    if isinstance(filtermanaged, Unset):
        json_filtermanaged = UNSET
    else:
        json_filtermanaged = filtermanaged
    params["filter[managed]"] = json_filtermanaged

    json_filterservice: None | str | Unset
    if isinstance(filterservice, Unset):
        json_filterservice = UNSET
    else:
        json_filterservice = filterservice
    params["filter[service]"] = json_filterservice

    json_filterlast_seen: None | str | Unset
    if isinstance(filterlast_seen, Unset):
        json_filterlast_seen = UNSET
    else:
        json_filterlast_seen = filterlast_seen
    params["filter[last_seen]"] = json_filterlast_seen

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/loggers",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | LoggerListResponse | None:
    if response.status_code == 200:
        response_200 = LoggerListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | LoggerListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filtermanaged: bool | None | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
    filterlast_seen: None | str | Unset = UNSET,
) -> Response[ErrorResponse | LoggerListResponse]:
    """List Loggers

     List all loggers for the authenticated account. Optionally filter by managed status,
    service, or last-seen time window.

    Args:
        filtermanaged (bool | None | Unset):
        filterservice (None | str | Unset):
        filterlast_seen (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | LoggerListResponse]
    """

    kwargs = _get_kwargs(
        filtermanaged=filtermanaged,
        filterservice=filterservice,
        filterlast_seen=filterlast_seen,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtermanaged: bool | None | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
    filterlast_seen: None | str | Unset = UNSET,
) -> ErrorResponse | LoggerListResponse | None:
    """List Loggers

     List all loggers for the authenticated account. Optionally filter by managed status,
    service, or last-seen time window.

    Args:
        filtermanaged (bool | None | Unset):
        filterservice (None | str | Unset):
        filterlast_seen (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | LoggerListResponse
    """

    return sync_detailed(
        client=client,
        filtermanaged=filtermanaged,
        filterservice=filterservice,
        filterlast_seen=filterlast_seen,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtermanaged: bool | None | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
    filterlast_seen: None | str | Unset = UNSET,
) -> Response[ErrorResponse | LoggerListResponse]:
    """List Loggers

     List all loggers for the authenticated account. Optionally filter by managed status,
    service, or last-seen time window.

    Args:
        filtermanaged (bool | None | Unset):
        filterservice (None | str | Unset):
        filterlast_seen (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | LoggerListResponse]
    """

    kwargs = _get_kwargs(
        filtermanaged=filtermanaged,
        filterservice=filterservice,
        filterlast_seen=filterlast_seen,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtermanaged: bool | None | Unset = UNSET,
    filterservice: None | str | Unset = UNSET,
    filterlast_seen: None | str | Unset = UNSET,
) -> ErrorResponse | LoggerListResponse | None:
    """List Loggers

     List all loggers for the authenticated account. Optionally filter by managed status,
    service, or last-seen time window.

    Args:
        filtermanaged (bool | None | Unset):
        filterservice (None | str | Unset):
        filterlast_seen (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | LoggerListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filtermanaged=filtermanaged,
            filterservice=filterservice,
            filterlast_seen=filterlast_seen,
        )
    ).parsed
