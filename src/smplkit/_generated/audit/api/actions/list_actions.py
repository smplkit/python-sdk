from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.action_list_response import ActionListResponse
from ...models.list_actions_sort import ListActionsSort
from ...types import Unset


def _get_kwargs(
    *,
    filterresource_type: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
    sort: ListActionsSort | Unset = "key",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterresource_type: None | str | Unset
    if isinstance(filterresource_type, Unset):
        json_filterresource_type = UNSET
    else:
        json_filterresource_type = filterresource_type
    params["filter[resource_type]"] = json_filterresource_type

    json_pagesize: int | None | Unset
    if isinstance(pagesize, Unset):
        json_pagesize = UNSET
    else:
        json_pagesize = pagesize
    params["page[size]"] = json_pagesize

    json_pageafter: None | str | Unset
    if isinstance(pageafter, Unset):
        json_pageafter = UNSET
    else:
        json_pageafter = pageafter
    params["page[after]"] = json_pageafter

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort

    params["sort"] = json_sort

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/actions",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ActionListResponse | None:
    if response.status_code == 200:
        response_200 = ActionListResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ActionListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterresource_type: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
    sort: ListActionsSort | Unset = "key",
) -> Response[ActionListResponse]:
    """List Actions

     List the distinct `action` slugs recorded for this account.

    Default sort is `key` ascending; pass `sort=-key` for descending.
    Without `filter[resource_type]`, returns one row per distinct
    action. With `filter[resource_type]`, returns the actions recorded
    for that specific resource type.

    Args:
        filterresource_type (None | str | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):
        sort (ListActionsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `key`, `-key`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActionListResponse]
    """

    kwargs = _get_kwargs(
        filterresource_type=filterresource_type,
        pagesize=pagesize,
        pageafter=pageafter,
        sort=sort,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterresource_type: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
    sort: ListActionsSort | Unset = "key",
) -> ActionListResponse | None:
    """List Actions

     List the distinct `action` slugs recorded for this account.

    Default sort is `key` ascending; pass `sort=-key` for descending.
    Without `filter[resource_type]`, returns one row per distinct
    action. With `filter[resource_type]`, returns the actions recorded
    for that specific resource type.

    Args:
        filterresource_type (None | str | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):
        sort (ListActionsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `key`, `-key`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActionListResponse
    """

    return sync_detailed(
        client=client,
        filterresource_type=filterresource_type,
        pagesize=pagesize,
        pageafter=pageafter,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterresource_type: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
    sort: ListActionsSort | Unset = "key",
) -> Response[ActionListResponse]:
    """List Actions

     List the distinct `action` slugs recorded for this account.

    Default sort is `key` ascending; pass `sort=-key` for descending.
    Without `filter[resource_type]`, returns one row per distinct
    action. With `filter[resource_type]`, returns the actions recorded
    for that specific resource type.

    Args:
        filterresource_type (None | str | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):
        sort (ListActionsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `key`, `-key`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActionListResponse]
    """

    kwargs = _get_kwargs(
        filterresource_type=filterresource_type,
        pagesize=pagesize,
        pageafter=pageafter,
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterresource_type: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
    sort: ListActionsSort | Unset = "key",
) -> ActionListResponse | None:
    """List Actions

     List the distinct `action` slugs recorded for this account.

    Default sort is `key` ascending; pass `sort=-key` for descending.
    Without `filter[resource_type]`, returns one row per distinct
    action. With `filter[resource_type]`, returns the actions recorded
    for that specific resource type.

    Args:
        filterresource_type (None | str | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):
        sort (ListActionsSort | Unset): Field to sort by. Prefix with `-` for descending order.
            Default: `key`. Allowed values: `key`, `-key`. Default: 'key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActionListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterresource_type=filterresource_type,
            pagesize=pagesize,
            pageafter=pageafter,
            sort=sort,
        )
    ).parsed
