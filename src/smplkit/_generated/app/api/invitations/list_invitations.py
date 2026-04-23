from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.invitation_list_response import InvitationListResponse
from ...types import Unset


def _get_kwargs(
    *,
    filterstatus: None | str | Unset = UNSET,
    filtertoken: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filterstatus: None | str | Unset
    if isinstance(filterstatus, Unset):
        json_filterstatus = UNSET
    else:
        json_filterstatus = filterstatus
    params["filter[status]"] = json_filterstatus

    json_filtertoken: None | str | Unset
    if isinstance(filtertoken, Unset):
        json_filtertoken = UNSET
    else:
        json_filtertoken = filtertoken
    params["filter[token]"] = json_filtertoken

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/invitations",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | InvitationListResponse | None:
    if response.status_code == 200:
        response_200 = InvitationListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | InvitationListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filterstatus: None | str | Unset = UNSET,
    filtertoken: None | str | Unset = UNSET,
) -> Response[ErrorResponse | InvitationListResponse]:
    """List Invitations

     List invitations. Authenticated admins list invitations for their own account and may narrow by
    status. Unauthenticated callers must pass ``filter[token]`` to look up a specific invitation by its
    token — used to render the invitation preview before sign-in. The token-filter path always returns
    an array of 0 or 1 elements.

    Args:
        filterstatus (None | str | Unset):
        filtertoken (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | InvitationListResponse]
    """

    kwargs = _get_kwargs(
        filterstatus=filterstatus,
        filtertoken=filtertoken,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filterstatus: None | str | Unset = UNSET,
    filtertoken: None | str | Unset = UNSET,
) -> ErrorResponse | InvitationListResponse | None:
    """List Invitations

     List invitations. Authenticated admins list invitations for their own account and may narrow by
    status. Unauthenticated callers must pass ``filter[token]`` to look up a specific invitation by its
    token — used to render the invitation preview before sign-in. The token-filter path always returns
    an array of 0 or 1 elements.

    Args:
        filterstatus (None | str | Unset):
        filtertoken (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | InvitationListResponse
    """

    return sync_detailed(
        client=client,
        filterstatus=filterstatus,
        filtertoken=filtertoken,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filterstatus: None | str | Unset = UNSET,
    filtertoken: None | str | Unset = UNSET,
) -> Response[ErrorResponse | InvitationListResponse]:
    """List Invitations

     List invitations. Authenticated admins list invitations for their own account and may narrow by
    status. Unauthenticated callers must pass ``filter[token]`` to look up a specific invitation by its
    token — used to render the invitation preview before sign-in. The token-filter path always returns
    an array of 0 or 1 elements.

    Args:
        filterstatus (None | str | Unset):
        filtertoken (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | InvitationListResponse]
    """

    kwargs = _get_kwargs(
        filterstatus=filterstatus,
        filtertoken=filtertoken,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filterstatus: None | str | Unset = UNSET,
    filtertoken: None | str | Unset = UNSET,
) -> ErrorResponse | InvitationListResponse | None:
    """List Invitations

     List invitations. Authenticated admins list invitations for their own account and may narrow by
    status. Unauthenticated callers must pass ``filter[token]`` to look up a specific invitation by its
    token — used to render the invitation preview before sign-in. The token-filter path always returns
    an array of 0 or 1 elements.

    Args:
        filterstatus (None | str | Unset):
        filtertoken (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | InvitationListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filterstatus=filterstatus,
            filtertoken=filtertoken,
        )
    ).parsed
