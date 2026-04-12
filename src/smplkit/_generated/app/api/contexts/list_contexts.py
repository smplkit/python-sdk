from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.context_list_response import ContextListResponse
from ...models.error_response import ErrorResponse
from ...types import Unset


def _get_kwargs(
    *,
    filtercontext_type: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filtercontext_type: None | str | Unset
    if isinstance(filtercontext_type, Unset):
        json_filtercontext_type = UNSET
    else:
        json_filtercontext_type = filtercontext_type
    params["filter[context_type]"] = json_filtercontext_type

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/contexts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ContextListResponse | ErrorResponse | None:
    if response.status_code == 200:
        response_200 = ContextListResponse.from_dict(response.json())

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
) -> Response[ContextListResponse | ErrorResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
) -> Response[ContextListResponse | ErrorResponse]:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        filtercontext_type=filtercontext_type,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
) -> ContextListResponse | ErrorResponse | None:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextListResponse | ErrorResponse
    """

    return sync_detailed(
        client=client,
        filtercontext_type=filtercontext_type,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
) -> Response[ContextListResponse | ErrorResponse]:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        filtercontext_type=filtercontext_type,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
) -> ContextListResponse | ErrorResponse | None:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextListResponse | ErrorResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filtercontext_type=filtercontext_type,
        )
    ).parsed
