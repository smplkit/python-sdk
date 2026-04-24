from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.flag_list_response import FlagListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filtertype: None | str | Unset = UNSET,
    filtermanaged: bool | None | Unset = UNSET,
    filterreferences_context: None | str | Unset = UNSET,
    filterreferences_context_type: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filtertype: None | str | Unset
    if isinstance(filtertype, Unset):
        json_filtertype = UNSET
    else:
        json_filtertype = filtertype
    params["filter[type]"] = json_filtertype

    json_filtermanaged: bool | None | Unset
    if isinstance(filtermanaged, Unset):
        json_filtermanaged = UNSET
    else:
        json_filtermanaged = filtermanaged
    params["filter[managed]"] = json_filtermanaged

    json_filterreferences_context: None | str | Unset
    if isinstance(filterreferences_context, Unset):
        json_filterreferences_context = UNSET
    else:
        json_filterreferences_context = filterreferences_context
    params["filter[references_context]"] = json_filterreferences_context

    json_filterreferences_context_type: None | str | Unset
    if isinstance(filterreferences_context_type, Unset):
        json_filterreferences_context_type = UNSET
    else:
        json_filterreferences_context_type = filterreferences_context_type
    params["filter[references_context_type]"] = json_filterreferences_context_type

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/flags",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> FlagListResponse | None:
    if response.status_code == 200:
        response_200 = FlagListResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[FlagListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filtertype: None | str | Unset = UNSET,
    filtermanaged: bool | None | Unset = UNSET,
    filterreferences_context: None | str | Unset = UNSET,
    filterreferences_context_type: None | str | Unset = UNSET,
) -> Response[FlagListResponse]:
    """List Flags

     List all feature flags for the authenticated account.

    Args:
        filtertype (None | str | Unset):
        filtermanaged (bool | None | Unset):
        filterreferences_context (None | str | Unset): Return flags whose rules reference this
            context instance. Format: {type}:{key}
        filterreferences_context_type (None | str | Unset): Return flags whose rules reference any
            attribute of the given context type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FlagListResponse]
    """

    kwargs = _get_kwargs(
        filtertype=filtertype,
        filtermanaged=filtermanaged,
        filterreferences_context=filterreferences_context,
        filterreferences_context_type=filterreferences_context_type,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtertype: None | str | Unset = UNSET,
    filtermanaged: bool | None | Unset = UNSET,
    filterreferences_context: None | str | Unset = UNSET,
    filterreferences_context_type: None | str | Unset = UNSET,
) -> FlagListResponse | None:
    """List Flags

     List all feature flags for the authenticated account.

    Args:
        filtertype (None | str | Unset):
        filtermanaged (bool | None | Unset):
        filterreferences_context (None | str | Unset): Return flags whose rules reference this
            context instance. Format: {type}:{key}
        filterreferences_context_type (None | str | Unset): Return flags whose rules reference any
            attribute of the given context type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FlagListResponse
    """

    return sync_detailed(
        client=client,
        filtertype=filtertype,
        filtermanaged=filtermanaged,
        filterreferences_context=filterreferences_context,
        filterreferences_context_type=filterreferences_context_type,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtertype: None | str | Unset = UNSET,
    filtermanaged: bool | None | Unset = UNSET,
    filterreferences_context: None | str | Unset = UNSET,
    filterreferences_context_type: None | str | Unset = UNSET,
) -> Response[FlagListResponse]:
    """List Flags

     List all feature flags for the authenticated account.

    Args:
        filtertype (None | str | Unset):
        filtermanaged (bool | None | Unset):
        filterreferences_context (None | str | Unset): Return flags whose rules reference this
            context instance. Format: {type}:{key}
        filterreferences_context_type (None | str | Unset): Return flags whose rules reference any
            attribute of the given context type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FlagListResponse]
    """

    kwargs = _get_kwargs(
        filtertype=filtertype,
        filtermanaged=filtermanaged,
        filterreferences_context=filterreferences_context,
        filterreferences_context_type=filterreferences_context_type,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtertype: None | str | Unset = UNSET,
    filtermanaged: bool | None | Unset = UNSET,
    filterreferences_context: None | str | Unset = UNSET,
    filterreferences_context_type: None | str | Unset = UNSET,
) -> FlagListResponse | None:
    """List Flags

     List all feature flags for the authenticated account.

    Args:
        filtertype (None | str | Unset):
        filtermanaged (bool | None | Unset):
        filterreferences_context (None | str | Unset): Return flags whose rules reference this
            context instance. Format: {type}:{key}
        filterreferences_context_type (None | str | Unset): Return flags whose rules reference any
            attribute of the given context type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FlagListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filtertype=filtertype,
            filtermanaged=filtermanaged,
            filterreferences_context=filterreferences_context,
            filterreferences_context_type=filterreferences_context_type,
        )
    ).parsed
