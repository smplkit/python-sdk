from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.api_key_list_response import ApiKeyListResponse
from ...models.error_response import ErrorResponse
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union



def _get_kwargs(
    *,
    environment_id: Union[None, Unset, str] = UNSET,
    type_: Union[None, Unset, str] = UNSET,
    status: Union[None, Unset, str] = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_environment_id: Union[None, Unset, str]
    if isinstance(environment_id, Unset):
        json_environment_id = UNSET
    else:
        json_environment_id = environment_id
    params["environment_id"] = json_environment_id

    json_type_: Union[None, Unset, str]
    if isinstance(type_, Unset):
        json_type_ = UNSET
    else:
        json_type_ = type_
    params["type"] = json_type_

    json_status: Union[None, Unset, str]
    if isinstance(status, Unset):
        json_status = UNSET
    else:
        json_status = status
    params["status"] = json_status


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/api_keys",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[ApiKeyListResponse, ErrorResponse]]:
    if response.status_code == 200:
        response_200 = ApiKeyListResponse.from_dict(response.json())



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


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[ApiKeyListResponse, ErrorResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    environment_id: Union[None, Unset, str] = UNSET,
    type_: Union[None, Unset, str] = UNSET,
    status: Union[None, Unset, str] = UNSET,

) -> Response[Union[ApiKeyListResponse, ErrorResponse]]:
    """ List API Keys

    Args:
        environment_id (Union[None, Unset, str]):
        type_ (Union[None, Unset, str]):
        status (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiKeyListResponse, ErrorResponse]]
     """


    kwargs = _get_kwargs(
        environment_id=environment_id,
type_=type_,
status=status,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    environment_id: Union[None, Unset, str] = UNSET,
    type_: Union[None, Unset, str] = UNSET,
    status: Union[None, Unset, str] = UNSET,

) -> Optional[Union[ApiKeyListResponse, ErrorResponse]]:
    """ List API Keys

    Args:
        environment_id (Union[None, Unset, str]):
        type_ (Union[None, Unset, str]):
        status (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiKeyListResponse, ErrorResponse]
     """


    return sync_detailed(
        client=client,
environment_id=environment_id,
type_=type_,
status=status,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    environment_id: Union[None, Unset, str] = UNSET,
    type_: Union[None, Unset, str] = UNSET,
    status: Union[None, Unset, str] = UNSET,

) -> Response[Union[ApiKeyListResponse, ErrorResponse]]:
    """ List API Keys

    Args:
        environment_id (Union[None, Unset, str]):
        type_ (Union[None, Unset, str]):
        status (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiKeyListResponse, ErrorResponse]]
     """


    kwargs = _get_kwargs(
        environment_id=environment_id,
type_=type_,
status=status,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    environment_id: Union[None, Unset, str] = UNSET,
    type_: Union[None, Unset, str] = UNSET,
    status: Union[None, Unset, str] = UNSET,

) -> Optional[Union[ApiKeyListResponse, ErrorResponse]]:
    """ List API Keys

    Args:
        environment_id (Union[None, Unset, str]):
        type_ (Union[None, Unset, str]):
        status (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiKeyListResponse, ErrorResponse]
     """


    return (await asyncio_detailed(
        client=client,
environment_id=environment_id,
type_=type_,
status=status,

    )).parsed
