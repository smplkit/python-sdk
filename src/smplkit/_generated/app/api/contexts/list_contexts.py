from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.context_list_response import ContextListResponse
from ...models.error_response import ErrorResponse
from ...models.list_contexts_sort import ListContextsSort
from ...types import Unset


def _get_kwargs(
    *,
    filtercontext_type: None | str | Unset = UNSET,
    sort: ListContextsSort | Unset = "key",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filtercontext_type: None | str | Unset
    if isinstance(filtercontext_type, Unset):
        json_filtercontext_type = UNSET
    else:
        json_filtercontext_type = filtercontext_type
    params["filter[context_type]"] = json_filtercontext_type

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort

    params["sort"] = json_sort

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
    sort: ListContextsSort | Unset = "key",
) -> Response[ContextListResponse | ErrorResponse]:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):
        sort (ListContextsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        filtercontext_type=filtercontext_type,
        sort=sort,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
    sort: ListContextsSort | Unset = "key",
) -> ContextListResponse | ErrorResponse | None:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):
        sort (ListContextsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextListResponse | ErrorResponse
    """

    return sync_detailed(
        client=client,
        filtercontext_type=filtercontext_type,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
    sort: ListContextsSort | Unset = "key",
) -> Response[ContextListResponse | ErrorResponse]:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):
        sort (ListContextsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        filtercontext_type=filtercontext_type,
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtercontext_type: None | str | Unset = UNSET,
    sort: ListContextsSort | Unset = "key",
) -> ContextListResponse | ErrorResponse | None:
    """List Contexts

     List all context instances for the authenticated account.

    Args:
        filtercontext_type (None | str | Unset):
        sort (ListContextsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

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
            sort=sort,
        )
    ).parsed
