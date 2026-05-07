from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response
from ... import errors

from ...models.forwarder_response import ForwarderResponse
from uuid import UUID


def _get_kwargs(
    forwarder_id: UUID,
    *,
    body: ForwarderResponse,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v1/forwarders/{forwarder_id}".format(
            forwarder_id=quote(str(forwarder_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ForwarderResponse | None:
    if response.status_code == 200:
        response_200 = ForwarderResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ForwarderResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    forwarder_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ForwarderResponse,
) -> Response[ForwarderResponse]:
    r"""Update Forwarder

     Full-replace update. PUT semantics — every field is overwritten.

    The header values must be re-supplied; the GET path redacts them, but
    a PUT body that contains ``\"<redacted>\"`` would persist that literal.
    Customers must round-trip the actual secret back. This is the standard
    get-mutate-put pattern (see CLAUDE.md \"Updating Resources via the
    API\"); the SDK helpers track the un-redacted secret client-side so
    customers don't usually need to re-enter it.

    Args:
        forwarder_id (UUID):
        body (ForwarderResponse):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ForwarderResponse]
    """

    kwargs = _get_kwargs(
        forwarder_id=forwarder_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    forwarder_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ForwarderResponse,
) -> ForwarderResponse | None:
    r"""Update Forwarder

     Full-replace update. PUT semantics — every field is overwritten.

    The header values must be re-supplied; the GET path redacts them, but
    a PUT body that contains ``\"<redacted>\"`` would persist that literal.
    Customers must round-trip the actual secret back. This is the standard
    get-mutate-put pattern (see CLAUDE.md \"Updating Resources via the
    API\"); the SDK helpers track the un-redacted secret client-side so
    customers don't usually need to re-enter it.

    Args:
        forwarder_id (UUID):
        body (ForwarderResponse):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ForwarderResponse
    """

    return sync_detailed(
        forwarder_id=forwarder_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    forwarder_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ForwarderResponse,
) -> Response[ForwarderResponse]:
    r"""Update Forwarder

     Full-replace update. PUT semantics — every field is overwritten.

    The header values must be re-supplied; the GET path redacts them, but
    a PUT body that contains ``\"<redacted>\"`` would persist that literal.
    Customers must round-trip the actual secret back. This is the standard
    get-mutate-put pattern (see CLAUDE.md \"Updating Resources via the
    API\"); the SDK helpers track the un-redacted secret client-side so
    customers don't usually need to re-enter it.

    Args:
        forwarder_id (UUID):
        body (ForwarderResponse):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ForwarderResponse]
    """

    kwargs = _get_kwargs(
        forwarder_id=forwarder_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    forwarder_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ForwarderResponse,
) -> ForwarderResponse | None:
    r"""Update Forwarder

     Full-replace update. PUT semantics — every field is overwritten.

    The header values must be re-supplied; the GET path redacts them, but
    a PUT body that contains ``\"<redacted>\"`` would persist that literal.
    Customers must round-trip the actual secret back. This is the standard
    get-mutate-put pattern (see CLAUDE.md \"Updating Resources via the
    API\"); the SDK helpers track the un-redacted secret client-side so
    customers don't usually need to re-enter it.

    Args:
        forwarder_id (UUID):
        body (ForwarderResponse):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ForwarderResponse
    """

    return (
        await asyncio_detailed(
            forwarder_id=forwarder_id,
            client=client,
            body=body,
        )
    ).parsed
