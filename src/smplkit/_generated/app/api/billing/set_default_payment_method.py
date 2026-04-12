from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.payment_method_list_response import PaymentMethodListResponse
from ...models.set_default_payment_method_request import SetDefaultPaymentMethodRequest


def _get_kwargs(
    *,
    body: SetDefaultPaymentMethodRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/payment_methods",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | PaymentMethodListResponse | None:
    if response.status_code == 200:
        response_200 = PaymentMethodListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | PaymentMethodListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: SetDefaultPaymentMethodRequest,
) -> Response[ErrorResponse | PaymentMethodListResponse]:
    """Set Default Payment Method

     Attach a payment method to the account's Stripe Customer and set it as the default.

    Called by the frontend after ``stripe.confirmSetup()`` to persist the new card
    as the customer's ``invoice_settings.default_payment_method``.

    Args:
        body (SetDefaultPaymentMethodRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | PaymentMethodListResponse]
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
    body: SetDefaultPaymentMethodRequest,
) -> ErrorResponse | PaymentMethodListResponse | None:
    """Set Default Payment Method

     Attach a payment method to the account's Stripe Customer and set it as the default.

    Called by the frontend after ``stripe.confirmSetup()`` to persist the new card
    as the customer's ``invoice_settings.default_payment_method``.

    Args:
        body (SetDefaultPaymentMethodRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | PaymentMethodListResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: SetDefaultPaymentMethodRequest,
) -> Response[ErrorResponse | PaymentMethodListResponse]:
    """Set Default Payment Method

     Attach a payment method to the account's Stripe Customer and set it as the default.

    Called by the frontend after ``stripe.confirmSetup()`` to persist the new card
    as the customer's ``invoice_settings.default_payment_method``.

    Args:
        body (SetDefaultPaymentMethodRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | PaymentMethodListResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: SetDefaultPaymentMethodRequest,
) -> ErrorResponse | PaymentMethodListResponse | None:
    """Set Default Payment Method

     Attach a payment method to the account's Stripe Customer and set it as the default.

    Called by the frontend after ``stripe.confirmSetup()`` to persist the new card
    as the customer's ``invoice_settings.default_payment_method``.

    Args:
        body (SetDefaultPaymentMethodRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | PaymentMethodListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
