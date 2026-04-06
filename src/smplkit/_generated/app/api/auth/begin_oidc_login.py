from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.oidc_provider import OidcProvider
from ...types import Unset


def _get_kwargs(
    provider: OidcProvider,
    *,
    mode: str | Unset = "signin",
    source: str | Unset = "",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["mode"] = mode

    params["source"] = source

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/auth/oidc/{provider}".format(
            provider=quote(str(provider), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | ErrorResponse | None:
    if response.status_code == 200:
        response_200 = response.json()
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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | ErrorResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    provider: OidcProvider,
    *,
    client: AuthenticatedClient | Client,
    mode: str | Unset = "signin",
    source: str | Unset = "",
) -> Response[Any | ErrorResponse]:
    """Begin OIDC Login

     Initiates the OIDC authorization flow by redirecting the user to the provider's login page.

    Args:
        provider (OidcProvider):
        mode (str | Unset):  Default: 'signin'.
        source (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorResponse]
    """

    kwargs = _get_kwargs(
        provider=provider,
        mode=mode,
        source=source,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    provider: OidcProvider,
    *,
    client: AuthenticatedClient | Client,
    mode: str | Unset = "signin",
    source: str | Unset = "",
) -> Any | ErrorResponse | None:
    """Begin OIDC Login

     Initiates the OIDC authorization flow by redirecting the user to the provider's login page.

    Args:
        provider (OidcProvider):
        mode (str | Unset):  Default: 'signin'.
        source (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorResponse
    """

    return sync_detailed(
        provider=provider,
        client=client,
        mode=mode,
        source=source,
    ).parsed


async def asyncio_detailed(
    provider: OidcProvider,
    *,
    client: AuthenticatedClient | Client,
    mode: str | Unset = "signin",
    source: str | Unset = "",
) -> Response[Any | ErrorResponse]:
    """Begin OIDC Login

     Initiates the OIDC authorization flow by redirecting the user to the provider's login page.

    Args:
        provider (OidcProvider):
        mode (str | Unset):  Default: 'signin'.
        source (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorResponse]
    """

    kwargs = _get_kwargs(
        provider=provider,
        mode=mode,
        source=source,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    provider: OidcProvider,
    *,
    client: AuthenticatedClient | Client,
    mode: str | Unset = "signin",
    source: str | Unset = "",
) -> Any | ErrorResponse | None:
    """Begin OIDC Login

     Initiates the OIDC authorization flow by redirecting the user to the provider's login page.

    Args:
        provider (OidcProvider):
        mode (str | Unset):  Default: 'signin'.
        source (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorResponse
    """

    return (
        await asyncio_detailed(
            provider=provider,
            client=client,
            mode=mode,
            source=source,
        )
    ).parsed
