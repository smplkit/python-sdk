from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.context_list_response import ContextListResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import Unset


def _get_kwargs(
    *,
    filtercontext_type_id: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filtercontext_type_id: None | str | Unset
    if isinstance(filtercontext_type_id, Unset):
        json_filtercontext_type_id = UNSET
    else:
        json_filtercontext_type_id = filtercontext_type_id
    params["filter[context_type_id]"] = json_filtercontext_type_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/contexts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ContextListResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ContextListResponse.from_dict(response.json())

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
) -> Response[ContextListResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filtercontext_type_id: None | str | Unset = UNSET,
) -> Response[ContextListResponse | HTTPValidationError]:
    """List Contexts

    Args:
        filtercontext_type_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextListResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        filtercontext_type_id=filtercontext_type_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filtercontext_type_id: None | str | Unset = UNSET,
) -> ContextListResponse | HTTPValidationError | None:
    """List Contexts

    Args:
        filtercontext_type_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextListResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        filtercontext_type_id=filtercontext_type_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filtercontext_type_id: None | str | Unset = UNSET,
) -> Response[ContextListResponse | HTTPValidationError]:
    """List Contexts

    Args:
        filtercontext_type_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContextListResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        filtercontext_type_id=filtercontext_type_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filtercontext_type_id: None | str | Unset = UNSET,
) -> ContextListResponse | HTTPValidationError | None:
    """List Contexts

    Args:
        filtercontext_type_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContextListResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            filtercontext_type_id=filtercontext_type_id,
        )
    ).parsed
