from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.subscription_response import SubscriptionResponse
from ...models.update_subscription_body import UpdateSubscriptionBody


def _get_kwargs(
    product: str,
    *,
    body: UpdateSubscriptionBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/v1/subscriptions/{product}".format(
            product=quote(str(product), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | SubscriptionResponse | None:
    if response.status_code == 200:
        response_200 = SubscriptionResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | SubscriptionResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    product: str,
    *,
    client: AuthenticatedClient,
    body: UpdateSubscriptionBody,
) -> Response[ErrorResponse | SubscriptionResponse]:
    """Update Subscription

     Change the plan for an existing paid subscription (upgrade or downgrade).

    Args:
        product (str):
        body (UpdateSubscriptionBody):  Example: {'data': {'attributes': {'plan': 'pro'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | SubscriptionResponse]
    """

    kwargs = _get_kwargs(
        product=product,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    product: str,
    *,
    client: AuthenticatedClient,
    body: UpdateSubscriptionBody,
) -> ErrorResponse | SubscriptionResponse | None:
    """Update Subscription

     Change the plan for an existing paid subscription (upgrade or downgrade).

    Args:
        product (str):
        body (UpdateSubscriptionBody):  Example: {'data': {'attributes': {'plan': 'pro'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | SubscriptionResponse
    """

    return sync_detailed(
        product=product,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    product: str,
    *,
    client: AuthenticatedClient,
    body: UpdateSubscriptionBody,
) -> Response[ErrorResponse | SubscriptionResponse]:
    """Update Subscription

     Change the plan for an existing paid subscription (upgrade or downgrade).

    Args:
        product (str):
        body (UpdateSubscriptionBody):  Example: {'data': {'attributes': {'plan': 'pro'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | SubscriptionResponse]
    """

    kwargs = _get_kwargs(
        product=product,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    product: str,
    *,
    client: AuthenticatedClient,
    body: UpdateSubscriptionBody,
) -> ErrorResponse | SubscriptionResponse | None:
    """Update Subscription

     Change the plan for an existing paid subscription (upgrade or downgrade).

    Args:
        product (str):
        body (UpdateSubscriptionBody):  Example: {'data': {'attributes': {'plan': 'pro'}, 'type':
            'subscription'}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | SubscriptionResponse
    """

    return (
        await asyncio_detailed(
            product=product,
            client=client,
            body=body,
        )
    ).parsed
