from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.config_list_response import ConfigListResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import Unset


def _get_kwargs(
    *,
    filterkey: None | str | Unset = UNSET,
    filterparent: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterkey: None | str | Unset
    if isinstance(filterkey, Unset):
        json_filterkey = UNSET
    else:
        json_filterkey = filterkey
    params["filter[key]"] = json_filterkey

    json_filterparent: None | str | Unset
    if isinstance(filterparent, Unset):
        json_filterparent = UNSET
    else:
        json_filterparent = filterparent
    params["filter[parent]"] = json_filterparent

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/configs",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ConfigListResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ConfigListResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ConfigListResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterkey: None | str | Unset = UNSET,
    filterparent: None | str | Unset = UNSET,
) -> Response[ConfigListResponse | HTTPValidationError]:
    """List Configs

    Args:
        filterkey (None | str | Unset):
        filterparent (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConfigListResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        filterkey=filterkey,
        filterparent=filterparent,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterkey: None | str | Unset = UNSET,
    filterparent: None | str | Unset = UNSET,
) -> ConfigListResponse | HTTPValidationError | None:
    """List Configs

    Args:
        filterkey (None | str | Unset):
        filterparent (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConfigListResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        filterkey=filterkey,
        filterparent=filterparent,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterkey: None | str | Unset = UNSET,
    filterparent: None | str | Unset = UNSET,
) -> Response[ConfigListResponse | HTTPValidationError]:
    """List Configs

    Args:
        filterkey (None | str | Unset):
        filterparent (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConfigListResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        filterkey=filterkey,
        filterparent=filterparent,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterkey: None | str | Unset = UNSET,
    filterparent: None | str | Unset = UNSET,
) -> ConfigListResponse | HTTPValidationError | None:
    """List Configs

    Args:
        filterkey (None | str | Unset):
        filterparent (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConfigListResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            filterkey=filterkey,
            filterparent=filterparent,
        )
    ).parsed
