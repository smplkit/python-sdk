from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.user_list_response import UserListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filteraccount: None | str | Unset = UNSET,
    filteremail: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagenumber: int | Unset = 1,
    pagesize: int | Unset = 50,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filteraccount: None | str | Unset
    if isinstance(filteraccount, Unset):
        json_filteraccount = UNSET
    else:
        json_filteraccount = filteraccount
    params["filter[account]"] = json_filteraccount

    json_filteremail: None | str | Unset
    if isinstance(filteremail, Unset):
        json_filteremail = UNSET
    else:
        json_filteremail = filteremail
    params["filter[email]"] = json_filteremail

    json_filtersearch: None | str | Unset
    if isinstance(filtersearch, Unset):
        json_filtersearch = UNSET
    else:
        json_filtersearch = filtersearch
    params["filter[search]"] = json_filtersearch

    params["page[number]"] = pagenumber

    params["page[size]"] = pagesize

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/users",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | UserListResponse | None:
    if response.status_code == 200:
        response_200 = UserListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | UserListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filteraccount: None | str | Unset = UNSET,
    filteremail: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagenumber: int | Unset = 1,
    pagesize: int | Unset = 50,
) -> Response[ErrorResponse | UserListResponse]:
    """List Users

     List users in the authenticated account.

    Args:
        filteraccount (None | str | Unset):
        filteremail (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match against display_name
            and email. If the value is a valid UUID, also matches user id exactly.
        pagenumber (int | Unset): 1-based page number Default: 1.
        pagesize (int | Unset): Items per page Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | UserListResponse]
    """

    kwargs = _get_kwargs(
        filteraccount=filteraccount,
        filteremail=filteremail,
        filtersearch=filtersearch,
        pagenumber=pagenumber,
        pagesize=pagesize,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filteraccount: None | str | Unset = UNSET,
    filteremail: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagenumber: int | Unset = 1,
    pagesize: int | Unset = 50,
) -> ErrorResponse | UserListResponse | None:
    """List Users

     List users in the authenticated account.

    Args:
        filteraccount (None | str | Unset):
        filteremail (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match against display_name
            and email. If the value is a valid UUID, also matches user id exactly.
        pagenumber (int | Unset): 1-based page number Default: 1.
        pagesize (int | Unset): Items per page Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | UserListResponse
    """

    return sync_detailed(
        client=client,
        filteraccount=filteraccount,
        filteremail=filteremail,
        filtersearch=filtersearch,
        pagenumber=pagenumber,
        pagesize=pagesize,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filteraccount: None | str | Unset = UNSET,
    filteremail: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagenumber: int | Unset = 1,
    pagesize: int | Unset = 50,
) -> Response[ErrorResponse | UserListResponse]:
    """List Users

     List users in the authenticated account.

    Args:
        filteraccount (None | str | Unset):
        filteremail (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match against display_name
            and email. If the value is a valid UUID, also matches user id exactly.
        pagenumber (int | Unset): 1-based page number Default: 1.
        pagesize (int | Unset): Items per page Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | UserListResponse]
    """

    kwargs = _get_kwargs(
        filteraccount=filteraccount,
        filteremail=filteremail,
        filtersearch=filtersearch,
        pagenumber=pagenumber,
        pagesize=pagesize,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filteraccount: None | str | Unset = UNSET,
    filteremail: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagenumber: int | Unset = 1,
    pagesize: int | Unset = 50,
) -> ErrorResponse | UserListResponse | None:
    """List Users

     List users in the authenticated account.

    Args:
        filteraccount (None | str | Unset):
        filteremail (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match against display_name
            and email. If the value is a valid UUID, also matches user id exactly.
        pagenumber (int | Unset): 1-based page number Default: 1.
        pagesize (int | Unset): Items per page Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | UserListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filteraccount=filteraccount,
            filteremail=filteremail,
            filtersearch=filtersearch,
            pagenumber=pagenumber,
            pagesize=pagesize,
        )
    ).parsed
