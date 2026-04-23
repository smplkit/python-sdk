from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response
from ... import errors

from ...models.create_subscription_body import CreateSubscriptionBody
from ...models.error_response import ErrorResponse
from ...models.subscription_response import SubscriptionResponse


def _get_kwargs(
    *,
    body: CreateSubscriptionBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/subscriptions",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | SubscriptionResponse | None:
    if response.status_code == 201:
        response_201 = SubscriptionResponse.from_dict(response.json())

        return response_201

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
) -> Response[ErrorResponse | SubscriptionResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateSubscriptionBody,
) -> Response[ErrorResponse | SubscriptionResponse]:
    """Create Subscription

     Create a new paid subscription for a product.

    Args:
        body (CreateSubscriptionBody):  Example: {'data': {'attributes': {'payment_method':
            'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'plan': 'pro', 'product': 'flags'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | SubscriptionResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: CreateSubscriptionBody,
) -> ErrorResponse | SubscriptionResponse | None:
    """Create Subscription

     Create a new paid subscription for a product.

    Args:
        body (CreateSubscriptionBody):  Example: {'data': {'attributes': {'payment_method':
            'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'plan': 'pro', 'product': 'flags'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | SubscriptionResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateSubscriptionBody,
) -> Response[ErrorResponse | SubscriptionResponse]:
    """Create Subscription

     Create a new paid subscription for a product.

    Args:
        body (CreateSubscriptionBody):  Example: {'data': {'attributes': {'payment_method':
            'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'plan': 'pro', 'product': 'flags'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | SubscriptionResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateSubscriptionBody,
) -> ErrorResponse | SubscriptionResponse | None:
    """Create Subscription

     Create a new paid subscription for a product.

    Args:
        body (CreateSubscriptionBody):  Example: {'data': {'attributes': {'payment_method':
            'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'plan': 'pro', 'product': 'flags'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | SubscriptionResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
