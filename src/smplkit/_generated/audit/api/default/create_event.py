from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.event_response import EventResponse
from ...types import Unset


def _get_kwargs(
    *,
    body: EventResponse,
    idempotency_key: None | str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(idempotency_key, Unset):
        headers["Idempotency-Key"] = idempotency_key

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/events",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> EventResponse | None:
    if response.status_code == 200:
        response_200 = EventResponse.from_dict(response.json())

        return response_200

    if response.status_code == 201:
        response_201 = EventResponse.from_dict(response.json())

        return response_201

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[EventResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: EventResponse,
    idempotency_key: None | str | Unset = UNSET,
) -> Response[EventResponse]:
    """Create Event

     Record an audit event for the authenticated account.

    Returns ``201 Created`` on first write, ``200 OK`` if the request was a
    duplicate (matched by ``Idempotency-Key`` or auto-derived key).

    Customers may not emit events whose ``resource_type`` starts with
    ``smpl.`` — that namespace is reserved for smplkit-emitted events
    about platform resources.

    Args:
        idempotency_key (None | str | Unset):
        body (EventResponse): JSON:API single-resource response.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[EventResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        idempotency_key=idempotency_key,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: EventResponse,
    idempotency_key: None | str | Unset = UNSET,
) -> EventResponse | None:
    """Create Event

     Record an audit event for the authenticated account.

    Returns ``201 Created`` on first write, ``200 OK`` if the request was a
    duplicate (matched by ``Idempotency-Key`` or auto-derived key).

    Customers may not emit events whose ``resource_type`` starts with
    ``smpl.`` — that namespace is reserved for smplkit-emitted events
    about platform resources.

    Args:
        idempotency_key (None | str | Unset):
        body (EventResponse): JSON:API single-resource response.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        EventResponse
    """

    return sync_detailed(
        client=client,
        body=body,
        idempotency_key=idempotency_key,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: EventResponse,
    idempotency_key: None | str | Unset = UNSET,
) -> Response[EventResponse]:
    """Create Event

     Record an audit event for the authenticated account.

    Returns ``201 Created`` on first write, ``200 OK`` if the request was a
    duplicate (matched by ``Idempotency-Key`` or auto-derived key).

    Customers may not emit events whose ``resource_type`` starts with
    ``smpl.`` — that namespace is reserved for smplkit-emitted events
    about platform resources.

    Args:
        idempotency_key (None | str | Unset):
        body (EventResponse): JSON:API single-resource response.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[EventResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        idempotency_key=idempotency_key,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: EventResponse,
    idempotency_key: None | str | Unset = UNSET,
) -> EventResponse | None:
    """Create Event

     Record an audit event for the authenticated account.

    Returns ``201 Created`` on first write, ``200 OK`` if the request was a
    duplicate (matched by ``Idempotency-Key`` or auto-derived key).

    Customers may not emit events whose ``resource_type`` starts with
    ``smpl.`` — that namespace is reserved for smplkit-emitted events
    about platform resources.

    Args:
        idempotency_key (None | str | Unset):
        body (EventResponse): JSON:API single-resource response.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        EventResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            idempotency_key=idempotency_key,
        )
    ).parsed
