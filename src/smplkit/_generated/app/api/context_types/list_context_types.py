from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.context_type_list_response import ContextTypeListResponse
from ...models.error_response import ErrorResponse
from ...models.list_context_types_sort import ListContextTypesSort
from ...types import Unset


def _get_kwargs(
    *,
    sort: ListContextTypesSort | Unset = "key",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort

    params["sort"] = json_sort

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/context_types",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ContextTypeListResponse | ErrorResponse | None:
    if response.status_code == 200:
        response_200 = ContextTypeListResponse.from_dict(response.json())

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
) -> Response[ContextTypeListResponse | ErrorResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    sort: ListContextTypesSort | Unset = "key",
) -> Response[ContextTypeListResponse | ErrorResponse]:
    """List Context Types

     List all context types for the authenticated account.

    Args:
        sort (ListContextTypesSort | Unset): Field to sort by. Prefix with `-` for descending
            order. Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextTypeListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        sort=sort,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    sort: ListContextTypesSort | Unset = "key",
) -> ContextTypeListResponse | ErrorResponse | None:
    """List Context Types

     List all context types for the authenticated account.

    Args:
        sort (ListContextTypesSort | Unset): Field to sort by. Prefix with `-` for descending
            order. Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextTypeListResponse | ErrorResponse
    """

    return sync_detailed(
        client=client,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    sort: ListContextTypesSort | Unset = "key",
) -> Response[ContextTypeListResponse | ErrorResponse]:
    """List Context Types

     List all context types for the authenticated account.

    Args:
        sort (ListContextTypesSort | Unset): Field to sort by. Prefix with `-` for descending
            order. Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextTypeListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    sort: ListContextTypesSort | Unset = "key",
) -> ContextTypeListResponse | ErrorResponse | None:
    """List Context Types

     List all context types for the authenticated account.

    Args:
        sort (ListContextTypesSort | Unset): Field to sort by. Prefix with `-` for descending
            order. Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextTypeListResponse | ErrorResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            sort=sort,
        )
    ).parsed
