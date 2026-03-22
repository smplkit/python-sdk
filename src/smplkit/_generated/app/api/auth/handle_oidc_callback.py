from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.oidc_provider import check_oidc_provider
from ...models.oidc_provider import OidcProvider
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union



def _get_kwargs(
    provider: OidcProvider,
    *,
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    error_description: Union[None, Unset, str] = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_code: Union[None, Unset, str]
    if isinstance(code, Unset):
        json_code = UNSET
    else:
        json_code = code
    params["code"] = json_code

    json_state: Union[None, Unset, str]
    if isinstance(state, Unset):
        json_state = UNSET
    else:
        json_state = state
    params["state"] = json_state

    json_error: Union[None, Unset, str]
    if isinstance(error, Unset):
        json_error = UNSET
    else:
        json_error = error
    params["error"] = json_error

    json_error_description: Union[None, Unset, str]
    if isinstance(error_description, Unset):
        json_error_description = UNSET
    else:
        json_error_description = error_description
    params["error_description"] = json_error_description


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/auth/callback/{provider}".format(provider=provider,),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[Any, ErrorResponse]]:
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


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[Any, ErrorResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    provider: OidcProvider,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    error_description: Union[None, Unset, str] = UNSET,

) -> Response[Union[Any, ErrorResponse]]:
    """ Handle OIDC Callback

     Handles the callback from the OIDC provider, exchanges the authorization code for tokens, and
    redirects to the frontend.

    Args:
        provider (OidcProvider):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):
        error_description (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorResponse]]
     """


    kwargs = _get_kwargs(
        provider=provider,
code=code,
state=state,
error=error,
error_description=error_description,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    provider: OidcProvider,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    error_description: Union[None, Unset, str] = UNSET,

) -> Optional[Union[Any, ErrorResponse]]:
    """ Handle OIDC Callback

     Handles the callback from the OIDC provider, exchanges the authorization code for tokens, and
    redirects to the frontend.

    Args:
        provider (OidcProvider):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):
        error_description (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorResponse]
     """


    return sync_detailed(
        provider=provider,
client=client,
code=code,
state=state,
error=error,
error_description=error_description,

    ).parsed

async def asyncio_detailed(
    provider: OidcProvider,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    error_description: Union[None, Unset, str] = UNSET,

) -> Response[Union[Any, ErrorResponse]]:
    """ Handle OIDC Callback

     Handles the callback from the OIDC provider, exchanges the authorization code for tokens, and
    redirects to the frontend.

    Args:
        provider (OidcProvider):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):
        error_description (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorResponse]]
     """


    kwargs = _get_kwargs(
        provider=provider,
code=code,
state=state,
error=error,
error_description=error_description,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    provider: OidcProvider,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    error_description: Union[None, Unset, str] = UNSET,

) -> Optional[Union[Any, ErrorResponse]]:
    """ Handle OIDC Callback

     Handles the callback from the OIDC provider, exchanges the authorization code for tokens, and
    redirects to the frontend.

    Args:
        provider (OidcProvider):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):
        error_description (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorResponse]
     """


    return (await asyncio_detailed(
        provider=provider,
client=client,
code=code,
state=state,
error=error,
error_description=error_description,

    )).parsed
