from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.api_key_list_response import ApiKeyListResponse
from ...models.error_response import ErrorResponse
from ...types import Unset


def _get_kwargs(
    *,
    filterenvironment: None | str | Unset = UNSET,
    filtertype: None | str | Unset = UNSET,
    filterstatus: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterenvironment: None | str | Unset
    if isinstance(filterenvironment, Unset):
        json_filterenvironment = UNSET
    else:
        json_filterenvironment = filterenvironment
    params["filter[environment]"] = json_filterenvironment

    json_filtertype: None | str | Unset
    if isinstance(filtertype, Unset):
        json_filtertype = UNSET
    else:
        json_filtertype = filtertype
    params["filter[type]"] = json_filtertype

    json_filterstatus: None | str | Unset
    if isinstance(filterstatus, Unset):
        json_filterstatus = UNSET
    else:
        json_filterstatus = filterstatus
    params["filter[status]"] = json_filterstatus

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/api_keys",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ApiKeyListResponse | ErrorResponse | None:
    if response.status_code == 200:
        response_200 = ApiKeyListResponse.from_dict(response.json())

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
) -> Response[ApiKeyListResponse | ErrorResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filtertype: None | str | Unset = UNSET,
    filterstatus: None | str | Unset = UNSET,
) -> Response[ApiKeyListResponse | ErrorResponse]:
    """List API Keys

    Args:
        filterenvironment (None | str | Unset):
        filtertype (None | str | Unset):
        filterstatus (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiKeyListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        filterenvironment=filterenvironment,
        filtertype=filtertype,
        filterstatus=filterstatus,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filtertype: None | str | Unset = UNSET,
    filterstatus: None | str | Unset = UNSET,
) -> ApiKeyListResponse | ErrorResponse | None:
    """List API Keys

    Args:
        filterenvironment (None | str | Unset):
        filtertype (None | str | Unset):
        filterstatus (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiKeyListResponse | ErrorResponse
    """

    return sync_detailed(
        client=client,
        filterenvironment=filterenvironment,
        filtertype=filtertype,
        filterstatus=filterstatus,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filtertype: None | str | Unset = UNSET,
    filterstatus: None | str | Unset = UNSET,
) -> Response[ApiKeyListResponse | ErrorResponse]:
    """List API Keys

    Args:
        filterenvironment (None | str | Unset):
        filtertype (None | str | Unset):
        filterstatus (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiKeyListResponse | ErrorResponse]
    """

    kwargs = _get_kwargs(
        filterenvironment=filterenvironment,
        filtertype=filtertype,
        filterstatus=filterstatus,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterenvironment: None | str | Unset = UNSET,
    filtertype: None | str | Unset = UNSET,
    filterstatus: None | str | Unset = UNSET,
) -> ApiKeyListResponse | ErrorResponse | None:
    """List API Keys

    Args:
        filterenvironment (None | str | Unset):
        filtertype (None | str | Unset):
        filterstatus (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiKeyListResponse | ErrorResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterenvironment=filterenvironment,
            filtertype=filtertype,
            filterstatus=filterstatus,
        )
    ).parsed
