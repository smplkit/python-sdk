from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.forwarder_list_response import ForwarderListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filterforwarder_type: None | str | Unset = UNSET,
    filterenabled: bool | None | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterforwarder_type: None | str | Unset
    if isinstance(filterforwarder_type, Unset):
        json_filterforwarder_type = UNSET
    else:
        json_filterforwarder_type = filterforwarder_type
    params["filter[forwarder_type]"] = json_filterforwarder_type

    json_filterenabled: bool | None | Unset
    if isinstance(filterenabled, Unset):
        json_filterenabled = UNSET
    else:
        json_filterenabled = filterenabled
    params["filter[enabled]"] = json_filterenabled

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
        "url": "/api/v1/forwarders",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ForwarderListResponse | None:
    if response.status_code == 200:
        response_200 = ForwarderListResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ForwarderListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterforwarder_type: None | str | Unset = UNSET,
    filterenabled: bool | None | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> Response[ForwarderListResponse]:
    """List Forwarders

     List forwarders for the authenticated account.

    Reads do not require the entitlement — a downgraded account can still
    inspect what they configured, they just can't create new ones.

    Args:
        filterforwarder_type (None | str | Unset):
        filterenabled (bool | None | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ForwarderListResponse]
    """

    kwargs = _get_kwargs(
        filterforwarder_type=filterforwarder_type,
        filterenabled=filterenabled,
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
    filterforwarder_type: None | str | Unset = UNSET,
    filterenabled: bool | None | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> ForwarderListResponse | None:
    """List Forwarders

     List forwarders for the authenticated account.

    Reads do not require the entitlement — a downgraded account can still
    inspect what they configured, they just can't create new ones.

    Args:
        filterforwarder_type (None | str | Unset):
        filterenabled (bool | None | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ForwarderListResponse
    """

    return sync_detailed(
        client=client,
        filterforwarder_type=filterforwarder_type,
        filterenabled=filterenabled,
        pagesize=pagesize,
        pageafter=pageafter,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterforwarder_type: None | str | Unset = UNSET,
    filterenabled: bool | None | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> Response[ForwarderListResponse]:
    """List Forwarders

     List forwarders for the authenticated account.

    Reads do not require the entitlement — a downgraded account can still
    inspect what they configured, they just can't create new ones.

    Args:
        filterforwarder_type (None | str | Unset):
        filterenabled (bool | None | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ForwarderListResponse]
    """

    kwargs = _get_kwargs(
        filterforwarder_type=filterforwarder_type,
        filterenabled=filterenabled,
        pagesize=pagesize,
        pageafter=pageafter,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterforwarder_type: None | str | Unset = UNSET,
    filterenabled: bool | None | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> ForwarderListResponse | None:
    """List Forwarders

     List forwarders for the authenticated account.

    Reads do not require the entitlement — a downgraded account can still
    inspect what they configured, they just can't create new ones.

    Args:
        filterforwarder_type (None | str | Unset):
        filterenabled (bool | None | Unset):
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ForwarderListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterforwarder_type=filterforwarder_type,
            filterenabled=filterenabled,
            pagesize=pagesize,
            pageafter=pageafter,
        )
    ).parsed
