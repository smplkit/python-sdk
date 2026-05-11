from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define

from ..types import UNSET, Unset

from ..models.test_forwarder_request_method import check_test_forwarder_request_method
from ..models.test_forwarder_request_method import TestForwarderRequestMethod
from typing import cast

if TYPE_CHECKING:
    from ..models.http_header import HttpHeader


T = TypeVar("T", bound="TestForwarderRequest")


@_attrs_define
class TestForwarderRequest:
    """Inputs to the test-forwarder action.

    Mirrors a forwarder's HTTP destination configuration with one
    addition: `timeout_ms`, applied per-request and capped server-side.

        Attributes:
            url (str): Destination URL.
            method (TestForwarderRequestMethod | Unset): HTTP method used for the test request. Default: 'POST'.
            headers (list[HttpHeader] | Unset): HTTP headers attached to the test request.
            body (None | str | Unset): Request body. If omitted, an empty body is sent.
            success_status (str | Unset): HTTP response status that indicates success. Either a specific status code (e.g.
                `200`, `204`) or a status class (`1xx`, `2xx`, `3xx`, `4xx`, `5xx`). Default: '2xx'.
            timeout_ms (int | None | Unset): Per-request timeout in milliseconds. Capped at 30 seconds.
    """

    url: str
    method: TestForwarderRequestMethod | Unset = "POST"
    headers: list[HttpHeader] | Unset = UNSET
    body: None | str | Unset = UNSET
    success_status: str | Unset = "2xx"
    timeout_ms: int | None | Unset = UNSET

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

        timeout_ms: int | None | Unset
        if isinstance(self.timeout_ms, Unset):
            timeout_ms = UNSET
        else:
            timeout_ms = self.timeout_ms

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
        if timeout_ms is not UNSET:
            field_dict["timeout_ms"] = timeout_ms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.http_header import HttpHeader

        d = dict(src_dict)
        url = d.pop("url")

        _method = d.pop("method", UNSET)
        method: TestForwarderRequestMethod | Unset
        if isinstance(_method, Unset):
            method = UNSET
        else:
            method = check_test_forwarder_request_method(_method)

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

        def _parse_timeout_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        timeout_ms = _parse_timeout_ms(d.pop("timeout_ms", UNSET))

        test_forwarder_request = cls(
            url=url,
            method=method,
            headers=headers,
            body=body,
            success_status=success_status,
            timeout_ms=timeout_ms,
        )

        return test_forwarder_request
