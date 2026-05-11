from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define

from ..types import UNSET, Unset

from ..models.forwarder_http_method import check_forwarder_http_method
from ..models.forwarder_http_method import ForwarderHttpMethod
from typing import cast

if TYPE_CHECKING:
    from ..models.http_header import HttpHeader


T = TypeVar("T", bound="ForwarderHttp")


@_attrs_define
class ForwarderHttp:
    """HTTP request configuration used to deliver an event to the destination.

    Attributes:
        url (str): Destination URL.
        method (ForwarderHttpMethod | Unset): HTTP method used when delivering an event. Default: 'POST'.
        headers (list[HttpHeader] | Unset): HTTP headers attached to each delivery request.
        body (None | str | Unset): Request body sent to the destination. If omitted, the event JSON is sent as the body.
        success_status (str | Unset): HTTP response status that indicates a successful delivery. Either a specific
            status code (e.g. `200`, `204`) or a status class (`1xx`, `2xx`, `3xx`, `4xx`, `5xx`). Default: '2xx'.
    """

    url: str
    method: ForwarderHttpMethod | Unset = "POST"
    headers: list[HttpHeader] | Unset = UNSET
    body: None | str | Unset = UNSET
    success_status: str | Unset = "2xx"

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        method: str | Unset = UNSET
        if not isinstance(self.method, Unset):
            method = self.method

        headers: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.headers, Unset):
            headers = []
            for headers_item_data in self.headers:
                headers_item = headers_item_data.to_dict()
                headers.append(headers_item)

        body: None | str | Unset
        if isinstance(self.body, Unset):
            body = UNSET
        else:
            body = self.body

        success_status = self.success_status

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "url": url,
            }
        )
        if method is not UNSET:
            field_dict["method"] = method
        if headers is not UNSET:
            field_dict["headers"] = headers
        if body is not UNSET:
            field_dict["body"] = body
        if success_status is not UNSET:
            field_dict["success_status"] = success_status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.http_header import HttpHeader

        d = dict(src_dict)
        url = d.pop("url")

        _method = d.pop("method", UNSET)
        method: ForwarderHttpMethod | Unset
        if isinstance(_method, Unset):
            method = UNSET
        else:
            method = check_forwarder_http_method(_method)

        _headers = d.pop("headers", UNSET)
        headers: list[HttpHeader] | Unset = UNSET
        if _headers is not UNSET:
            headers = []
            for headers_item_data in _headers:
                headers_item = HttpHeader.from_dict(headers_item_data)

                headers.append(headers_item)

        def _parse_body(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        body = _parse_body(d.pop("body", UNSET))

        success_status = d.pop("success_status", UNSET)

        forwarder_http = cls(
            url=url,
            method=method,
            headers=headers,
            body=body,
            success_status=success_status,
        )

        return forwarder_http
