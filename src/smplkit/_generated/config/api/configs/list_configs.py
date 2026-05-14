from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.config_list_response import ConfigListResponse
from ...models.list_configs_sort import ListConfigsSort
from ...types import Unset


def _get_kwargs(
    *,
    filterparent: None | str | Unset = UNSET,
    sort: ListConfigsSort | Unset = "key",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterparent: None | str | Unset
    if isinstance(filterparent, Unset):
        json_filterparent = UNSET
    else:
        json_filterparent = filterparent
    params["filter[parent]"] = json_filterparent

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort

    params["sort"] = json_sort

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/configs",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ConfigListResponse | None:
    if response.status_code == 200:
        response_200 = ConfigListResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ConfigListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterparent: None | str | Unset = UNSET,
    sort: ListConfigsSort | Unset = "key",
) -> Response[ConfigListResponse]:
    """List Configs

     List configs for this account.

    Default sort is `key` ascending. Pass `filter[parent]=<parent_key>`
    to return only the direct children of a specific config.

    Args:
        filterparent (None | str | Unset):
        sort (ListConfigsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConfigListResponse]
    """

    kwargs = _get_kwargs(
        filterparent=filterparent,
        sort=sort,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterparent: None | str | Unset = UNSET,
    sort: ListConfigsSort | Unset = "key",
) -> ConfigListResponse | None:
    """List Configs

     List configs for this account.

    Default sort is `key` ascending. Pass `filter[parent]=<parent_key>`
    to return only the direct children of a specific config.

    Args:
        filterparent (None | str | Unset):
        sort (ListConfigsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConfigListResponse
    """

    return sync_detailed(
        client=client,
        filterparent=filterparent,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterparent: None | str | Unset = UNSET,
    sort: ListConfigsSort | Unset = "key",
) -> Response[ConfigListResponse]:
    """List Configs

     List configs for this account.

    Default sort is `key` ascending. Pass `filter[parent]=<parent_key>`
    to return only the direct children of a specific config.

    Args:
        filterparent (None | str | Unset):
        sort (ListConfigsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConfigListResponse]
    """

    kwargs = _get_kwargs(
        filterparent=filterparent,
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterparent: None | str | Unset = UNSET,
    sort: ListConfigsSort | Unset = "key",
) -> ConfigListResponse | None:
    """List Configs

     List configs for this account.

    Default sort is `key` ascending. Pass `filter[parent]=<parent_key>`
    to return only the direct children of a specific config.

    Args:
        filterparent (None | str | Unset):
        sort (ListConfigsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `created_at`, `-created_at`, `key`, `-key`, `name`,
            `-name`, `updated_at`, `-updated_at`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConfigListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterparent=filterparent,
            sort=sort,
        )
    ).parsed
