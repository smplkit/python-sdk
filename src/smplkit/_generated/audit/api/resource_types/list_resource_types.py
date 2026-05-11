from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.resource_type_list_response import ResourceTypeListResponse
from ...types import Unset


def _get_kwargs(
    *,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

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

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/resource_types",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ResourceTypeListResponse | None:
    if response.status_code == 200:
        response_200 = ResourceTypeListResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ResourceTypeListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> Response[ResourceTypeListResponse]:
    """List Resource Types

     List the distinct `resource_type` slugs recorded for this account.

    The resource `id` is the slug itself. Useful for populating filter
    dropdowns in a UI.

    Args:
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResourceTypeListResponse]
    """

    kwargs = _get_kwargs(
        pagesize=pagesize,
        pageafter=pageafter,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> ResourceTypeListResponse | None:
    """List Resource Types

     List the distinct `resource_type` slugs recorded for this account.

    The resource `id` is the slug itself. Useful for populating filter
    dropdowns in a UI.

    Args:
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ResourceTypeListResponse
    """

    return sync_detailed(
        client=client,
        pagesize=pagesize,
        pageafter=pageafter,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> Response[ResourceTypeListResponse]:
    """List Resource Types

     List the distinct `resource_type` slugs recorded for this account.

    The resource `id` is the slug itself. Useful for populating filter
    dropdowns in a UI.

    Args:
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResourceTypeListResponse]
    """

    kwargs = _get_kwargs(
        pagesize=pagesize,
        pageafter=pageafter,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> ResourceTypeListResponse | None:
    """List Resource Types

     List the distinct `resource_type` slugs recorded for this account.

    The resource `id` is the slug itself. Useful for populating filter
    dropdowns in a UI.

    Args:
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ResourceTypeListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            pagesize=pagesize,
            pageafter=pageafter,
        )
    ).parsed
