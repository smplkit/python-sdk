from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.http_header import HttpHeader


T = TypeVar("T", bound="ForwarderHttp")


@_attrs_define
class ForwarderHttp:
    """The destination HTTP request shape stored encrypted on a forwarder.

    ``success_status`` is either a single integer status (e.g. ``200``) or
    a class string like ``"2xx"``. Anything outside the matched set is
    treated as a delivery failure.

        Attributes:
            url (str):
            method (str | Unset):  Default: 'POST'.
            headers (list[HttpHeader] | Unset):
            body (None | str | Unset):
            success_status (int | str | Unset):  Default: '2xx'.
    """

    url: str
    method: str | Unset = "POST"
    headers: list[HttpHeader] | Unset = UNSET
    body: None | str | Unset = UNSET
    success_status: int | str | Unset = "2xx"

    def to_dict(self) -> dict[str, Any]:
        url = self.url

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

        success_status: int | str | Unset
        if isinstance(self.success_status, Unset):
            success_status = UNSET
        else:
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

        method = d.pop("method", UNSET)

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

        def _parse_success_status(data: object) -> int | str | Unset:
            if isinstance(data, Unset):
                return data
            return cast(int | str | Unset, data)

        success_status = _parse_success_status(d.pop("success_status", UNSET))

        forwarder_http = cls(
            url=url,
            method=method,
            headers=headers,
            body=body,
            success_status=success_status,
        )

        return forwarder_http
