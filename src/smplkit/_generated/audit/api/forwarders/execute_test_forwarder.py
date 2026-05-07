from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response
from ... import errors

from ...models.test_forwarder_request import TestForwarderRequest
from ...models.test_forwarder_response import TestForwarderResponse


def _get_kwargs(
    *,
    body: TestForwarderRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/functions/test_forwarder/actions/execute",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> TestForwarderResponse | None:
    if response.status_code == 200:
        response_200 = TestForwarderResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[TestForwarderResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: TestForwarderRequest,
) -> Response[TestForwarderResponse]:
    """Execute Test Forwarder

     Execute a prepared HTTP request server-side and return the response.

    The same SSRF guard that gates the in-line forwarder loop is applied
    here — internal/private addresses, link-local IPs (including the EC2
    metadata service at 169.254.169.254), unique-local IPv6, and ports
    outside the configured allowlist are all rejected.

    Args:
        body (TestForwarderRequest): Plain-JSON body for the test_forwarder execute action.

            Mirrors the encrypted ``ForwarderHttp`` shape with one addition —
            ``timeout_ms``, capped server-side.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[TestForwarderResponse]
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
    body: TestForwarderRequest,
) -> TestForwarderResponse | None:
    """Execute Test Forwarder

     Execute a prepared HTTP request server-side and return the response.

    The same SSRF guard that gates the in-line forwarder loop is applied
    here — internal/private addresses, link-local IPs (including the EC2
    metadata service at 169.254.169.254), unique-local IPv6, and ports
    outside the configured allowlist are all rejected.

    Args:
        body (TestForwarderRequest): Plain-JSON body for the test_forwarder execute action.

            Mirrors the encrypted ``ForwarderHttp`` shape with one addition —
            ``timeout_ms``, capped server-side.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        TestForwarderResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: TestForwarderRequest,
) -> Response[TestForwarderResponse]:
    """Execute Test Forwarder

     Execute a prepared HTTP request server-side and return the response.

    The same SSRF guard that gates the in-line forwarder loop is applied
    here — internal/private addresses, link-local IPs (including the EC2
    metadata service at 169.254.169.254), unique-local IPv6, and ports
    outside the configured allowlist are all rejected.

    Args:
        body (TestForwarderRequest): Plain-JSON body for the test_forwarder execute action.

            Mirrors the encrypted ``ForwarderHttp`` shape with one addition —
            ``timeout_ms``, capped server-side.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[TestForwarderResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: TestForwarderRequest,
) -> TestForwarderResponse | None:
    """Execute Test Forwarder

     Execute a prepared HTTP request server-side and return the response.

    The same SSRF guard that gates the in-line forwarder loop is applied
    here — internal/private addresses, link-local IPs (including the EC2
    metadata service at 169.254.169.254), unique-local IPv6, and ports
    outside the configured allowlist are all rejected.

    Args:
        body (TestForwarderRequest): Plain-JSON body for the test_forwarder execute action.

            Mirrors the encrypted ``ForwarderHttp`` shape with one addition —
            ``timeout_ms``, capped server-side.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        TestForwarderResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
