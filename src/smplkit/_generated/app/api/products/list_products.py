from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.list_products_sort import ListProductsSort
from ...models.product_list_response import ProductListResponse
from ...types import Unset


def _get_kwargs(
    *,
    sort: ListProductsSort | Unset = "display_name",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort

    params["sort"] = json_sort

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/products",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | ProductListResponse | None:
    if response.status_code == 200:
        response_200 = ProductListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | ProductListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    sort: ListProductsSort | Unset = "display_name",
) -> Response[ErrorResponse | ProductListResponse]:
    """List Products

     Return all flag-enabled products with their plans, limits, and
    marketing content.

    Default sort is `display_name` ascending.

    Args:
        sort (ListProductsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `display_name`. Allowed values: `display_name`, `-display_name`, `id`, `-id`.
            Default: 'display_name'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | ProductListResponse]
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
    client: AuthenticatedClient | Client,
    sort: ListProductsSort | Unset = "display_name",
) -> ErrorResponse | ProductListResponse | None:
    """List Products

     Return all flag-enabled products with their plans, limits, and
    marketing content.

    Default sort is `display_name` ascending.

    Args:
        sort (ListProductsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `display_name`. Allowed values: `display_name`, `-display_name`, `id`, `-id`.
            Default: 'display_name'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | ProductListResponse
    """

    return sync_detailed(
        client=client,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    sort: ListProductsSort | Unset = "display_name",
) -> Response[ErrorResponse | ProductListResponse]:
    """List Products

     Return all flag-enabled products with their plans, limits, and
    marketing content.

    Default sort is `display_name` ascending.

    Args:
        sort (ListProductsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `display_name`. Allowed values: `display_name`, `-display_name`, `id`, `-id`.
            Default: 'display_name'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | ProductListResponse]
    """

    kwargs = _get_kwargs(
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    sort: ListProductsSort | Unset = "display_name",
) -> ErrorResponse | ProductListResponse | None:
    """List Products

     Return all flag-enabled products with their plans, limits, and
    marketing content.

    Default sort is `display_name` ascending.

    Args:
        sort (ListProductsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `display_name`. Allowed values: `display_name`, `-display_name`, `id`, `-id`.
            Default: 'display_name'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | ProductListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            sort=sort,
        )
    ).parsed
