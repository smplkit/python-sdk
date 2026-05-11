from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.event_list_response import EventListResponse
from ...types import Unset
from uuid import UUID


def _get_kwargs(
    *,
    filteroccurred_at: None | str | Unset = UNSET,
    filteractor_type: None | str | Unset = UNSET,
    filteractor_id: None | Unset | UUID = UNSET,
    filteraction: None | str | Unset = UNSET,
    filterresource_type: None | str | Unset = UNSET,
    filterresource_id: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_filteroccurred_at: None | str | Unset
    if isinstance(filteroccurred_at, Unset):
        json_filteroccurred_at = UNSET
    else:
        json_filteroccurred_at = filteroccurred_at
    params["filter[occurred_at]"] = json_filteroccurred_at

    json_filteractor_type: None | str | Unset
    if isinstance(filteractor_type, Unset):
        json_filteractor_type = UNSET
    else:
        json_filteractor_type = filteractor_type
    params["filter[actor_type]"] = json_filteractor_type

    json_filteractor_id: None | str | Unset
    if isinstance(filteractor_id, Unset):
        json_filteractor_id = UNSET
    elif isinstance(filteractor_id, UUID):
        json_filteractor_id = str(filteractor_id)
    else:
        json_filteractor_id = filteractor_id
    params["filter[actor_id]"] = json_filteractor_id

    json_filteraction: None | str | Unset
    if isinstance(filteraction, Unset):
        json_filteraction = UNSET
    else:
        json_filteraction = filteraction
    params["filter[action]"] = json_filteraction

    json_filterresource_type: None | str | Unset
    if isinstance(filterresource_type, Unset):
        json_filterresource_type = UNSET
    else:
        json_filterresource_type = filterresource_type
    params["filter[resource_type]"] = json_filterresource_type

    json_filterresource_id: None | str | Unset
    if isinstance(filterresource_id, Unset):
        json_filterresource_id = UNSET
    else:
        json_filterresource_id = filterresource_id
    params["filter[resource_id]"] = json_filterresource_id

    json_filtersearch: None | str | Unset
    if isinstance(filtersearch, Unset):
        json_filtersearch = UNSET
    else:
        json_filtersearch = filtersearch
    params["filter[search]"] = json_filtersearch

    json_pagesize: int | None | Unset
    if isinstance(pagesize, Unset):
        json_pagesize = UNSET
    else:
        json_pagesize = pagesize
    params["page[size]"] = json_pagesize

    json_pageafter: None | str | Unset
    if isinstance(pageafter, Unset):
        json_pageafter = UNSET
    else:
        json_pageafter = pageafter
    params["page[after]"] = json_pageafter

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/events",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> EventListResponse | None:
    if response.status_code == 200:
        response_200 = EventListResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[EventListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    filteroccurred_at: None | str | Unset = UNSET,
    filteractor_type: None | str | Unset = UNSET,
    filteractor_id: None | Unset | UUID = UNSET,
    filteraction: None | str | Unset = UNSET,
    filterresource_type: None | str | Unset = UNSET,
    filterresource_id: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> Response[EventListResponse]:
    """List Events

     List audit events for the authenticated account.

    Default sort is ``-created_at``; cursor pagination via ``page[after]``
    (the opaque cursor returned in ``links.next``). Filters are exact-match
    except ``filter[occurred_at]`` which uses the platform's range
    notation (``[2026-01-01T00:00:00Z,*)``) and ``filter[search]`` which
    is a case-insensitive substring match (per ADR-014; targets
    ``resource_id`` only at this revision).

    Args:
        filteroccurred_at (None | str | Unset):
        filteractor_type (None | str | Unset):
        filteractor_id (None | Unset | UUID):
        filteraction (None | str | Unset):
        filterresource_type (None | str | Unset):
        filterresource_id (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match. Searches against
            ``resource_id`` only — see ADR-014 for the platform-wide ``filter[search]`` convention.
            Use ``filter[resource_id]`` for an exact match.
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[EventListResponse]
    """

    kwargs = _get_kwargs(
        filteroccurred_at=filteroccurred_at,
        filteractor_type=filteractor_type,
        filteractor_id=filteractor_id,
        filteraction=filteraction,
        filterresource_type=filterresource_type,
        filterresource_id=filterresource_id,
        filtersearch=filtersearch,
        pagesize=pagesize,
        pageafter=pageafter,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    filteroccurred_at: None | str | Unset = UNSET,
    filteractor_type: None | str | Unset = UNSET,
    filteractor_id: None | Unset | UUID = UNSET,
    filteraction: None | str | Unset = UNSET,
    filterresource_type: None | str | Unset = UNSET,
    filterresource_id: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> EventListResponse | None:
    """List Events

     List audit events for the authenticated account.

    Default sort is ``-created_at``; cursor pagination via ``page[after]``
    (the opaque cursor returned in ``links.next``). Filters are exact-match
    except ``filter[occurred_at]`` which uses the platform's range
    notation (``[2026-01-01T00:00:00Z,*)``) and ``filter[search]`` which
    is a case-insensitive substring match (per ADR-014; targets
    ``resource_id`` only at this revision).

    Args:
        filteroccurred_at (None | str | Unset):
        filteractor_type (None | str | Unset):
        filteractor_id (None | Unset | UUID):
        filteraction (None | str | Unset):
        filterresource_type (None | str | Unset):
        filterresource_id (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match. Searches against
            ``resource_id`` only — see ADR-014 for the platform-wide ``filter[search]`` convention.
            Use ``filter[resource_id]`` for an exact match.
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        EventListResponse
    """

    return sync_detailed(
        client=client,
        filteroccurred_at=filteroccurred_at,
        filteractor_type=filteractor_type,
        filteractor_id=filteractor_id,
        filteraction=filteraction,
        filterresource_type=filterresource_type,
        filterresource_id=filterresource_id,
        filtersearch=filtersearch,
        pagesize=pagesize,
        pageafter=pageafter,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    filteroccurred_at: None | str | Unset = UNSET,
    filteractor_type: None | str | Unset = UNSET,
    filteractor_id: None | Unset | UUID = UNSET,
    filteraction: None | str | Unset = UNSET,
    filterresource_type: None | str | Unset = UNSET,
    filterresource_id: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> Response[EventListResponse]:
    """List Events

     List audit events for the authenticated account.

    Default sort is ``-created_at``; cursor pagination via ``page[after]``
    (the opaque cursor returned in ``links.next``). Filters are exact-match
    except ``filter[occurred_at]`` which uses the platform's range
    notation (``[2026-01-01T00:00:00Z,*)``) and ``filter[search]`` which
    is a case-insensitive substring match (per ADR-014; targets
    ``resource_id`` only at this revision).

    Args:
        filteroccurred_at (None | str | Unset):
        filteractor_type (None | str | Unset):
        filteractor_id (None | Unset | UUID):
        filteraction (None | str | Unset):
        filterresource_type (None | str | Unset):
        filterresource_id (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match. Searches against
            ``resource_id`` only — see ADR-014 for the platform-wide ``filter[search]`` convention.
            Use ``filter[resource_id]`` for an exact match.
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[EventListResponse]
    """

    kwargs = _get_kwargs(
        filteroccurred_at=filteroccurred_at,
        filteractor_type=filteractor_type,
        filteractor_id=filteractor_id,
        filteraction=filteraction,
        filterresource_type=filterresource_type,
        filterresource_id=filterresource_id,
        filtersearch=filtersearch,
        pagesize=pagesize,
        pageafter=pageafter,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    filteroccurred_at: None | str | Unset = UNSET,
    filteractor_type: None | str | Unset = UNSET,
    filteractor_id: None | Unset | UUID = UNSET,
    filteraction: None | str | Unset = UNSET,
    filterresource_type: None | str | Unset = UNSET,
    filterresource_id: None | str | Unset = UNSET,
    filtersearch: None | str | Unset = UNSET,
    pagesize: int | None | Unset = UNSET,
    pageafter: None | str | Unset = UNSET,
) -> EventListResponse | None:
    """List Events

     List audit events for the authenticated account.

    Default sort is ``-created_at``; cursor pagination via ``page[after]``
    (the opaque cursor returned in ``links.next``). Filters are exact-match
    except ``filter[occurred_at]`` which uses the platform's range
    notation (``[2026-01-01T00:00:00Z,*)``) and ``filter[search]`` which
    is a case-insensitive substring match (per ADR-014; targets
    ``resource_id`` only at this revision).

    Args:
        filteroccurred_at (None | str | Unset):
        filteractor_type (None | str | Unset):
        filteractor_id (None | Unset | UUID):
        filteraction (None | str | Unset):
        filterresource_type (None | str | Unset):
        filterresource_id (None | str | Unset):
        filtersearch (None | str | Unset): Case-insensitive substring match. Searches against
            ``resource_id`` only — see ADR-014 for the platform-wide ``filter[search]`` convention.
            Use ``filter[resource_id]`` for an exact match.
        pagesize (int | None | Unset):
        pageafter (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        EventListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            filteroccurred_at=filteroccurred_at,
            filteractor_type=filteractor_type,
            filteractor_id=filteractor_id,
            filteraction=filteraction,
            filterresource_type=filterresource_type,
            filterresource_id=filterresource_id,
            filtersearch=filtersearch,
            pagesize=pagesize,
            pageafter=pageafter,
        )
    ).parsed
