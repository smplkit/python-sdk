"""Tests for the audit resource_types / actions / wipe wrapper surface.

httpx.MockTransport is used to drive the wrapper without touching the
network. Coverage target is 100% on every new line in
``smplkit.audit.client`` and ``smplkit.audit.models`` for these paths.
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit.audit import (
    Action,
    ActionListPage,
    AuditClient,
    ResourceType,
    ResourceTypeListPage,
    WipeResult,
)


def _client_with_handler(handler) -> AuditClient:
    transport = httpx.MockTransport(handler)
    c = AuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    c._auth.set_httpx_client(
        httpx.Client(transport=transport, base_url="https://audit.example.com")
    )
    return c


def _resource_type_resource(*, key: str, created_at: str = "2026-04-12T15:23:01Z") -> dict[str, Any]:
    return {
        "id": key,
        "type": "resource_type",
        "attributes": {"resource_type": key, "created_at": created_at},
    }


def _action_resource(*, key: str, created_at: str = "2026-04-12T15:23:01Z") -> dict[str, Any]:
    return {
        "id": key,
        "type": "action",
        "attributes": {"action": key, "created_at": created_at},
    }


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestModels:
    def test_resource_type_from_resource(self):
        rt = ResourceType._from_resource(_resource_type_resource(key="smpl.flag"))
        assert rt.id == "smpl.flag"
        assert rt.resource_type == "smpl.flag"
        assert rt.created_at.isoformat().startswith("2026-04-12")

    def test_resource_type_falls_back_to_id_when_attribute_missing(self):
        # Defensive: if the server ever omits ``attributes.resource_type``
        # the wrapper still surfaces the ``id`` so callers don't see
        # ``None`` — JSON:API guarantees ``id`` is always present.
        body = {
            "id": "smpl.flag",
            "attributes": {"created_at": "2026-04-12T15:23:01Z"},
        }
        rt = ResourceType._from_resource(body)
        assert rt.resource_type == "smpl.flag"

    def test_action_from_resource(self):
        a = Action._from_resource(_action_resource(key="smpl.flag.created"))
        assert a.id == "smpl.flag.created"
        assert a.action == "smpl.flag.created"
        assert a.created_at.isoformat().startswith("2026-04-12")

    def test_action_falls_back_to_id_when_attribute_missing(self):
        body = {"id": "x.y", "attributes": {"created_at": "2026-04-12T15:23:01Z"}}
        a = Action._from_resource(body)
        assert a.action == "x.y"

    def test_wipe_result_total_rows_deleted(self):
        body = {
            "wiped": True,
            "tables": {
                "audit_event": 12,
                "audit_event_quota": 1,
                "forwarder": 0,
                "forwarder_delivery": 4,
                "resource_type": 2,
                "action": 3,
            },
            "completed_at": "2026-05-08T19:31:24Z",
        }
        r = WipeResult._from_response(body)
        assert r.total_rows_deleted == 22
        assert r.audit_event == 12
        assert r.completed_at.isoformat().startswith("2026-05-08")

    def test_wipe_result_missing_tables_defaults_zero(self):
        body = {"completed_at": "2026-05-08T19:31:24Z"}
        r = WipeResult._from_response(body)
        assert r.total_rows_deleted == 0
        assert r.audit_event == 0


# ---------------------------------------------------------------------------
# resource_types.list
# ---------------------------------------------------------------------------


class TestResourceTypesList:
    def test_returns_sorted_rows(self):
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.method == "GET"
            assert "/api/v1/resource_types" in str(req.url)
            return httpx.Response(
                200,
                json={
                    "data": [
                        _resource_type_resource(key="account"),
                        _resource_type_resource(key="user"),
                    ],
                    "meta": {"page_size": 50},
                },
            )

        c = _client_with_handler(handler)
        try:
            page = c.resource_types.list()
        finally:
            c._close()
        assert isinstance(page, ResourceTypeListPage)
        assert len(page) == 2
        assert [r.id for r in page] == ["account", "user"]
        assert page.next_cursor is None

    def test_pagination_cursor_propagates(self):
        captured: list[str] = []

        def handler(req):
            captured.append(str(req.url))
            return httpx.Response(
                200,
                json={
                    "data": [_resource_type_resource(key="alpha")],
                    "links": {
                        "next": "/api/v1/resource_types?page[size]=1&page[after]=tok-2"
                    },
                    "meta": {"page_size": 1},
                },
            )

        c = _client_with_handler(handler)
        try:
            page = c.resource_types.list(page_size=1, page_after="tok-1")
        finally:
            c._close()

        # Wrapper sent the page params on the wire.
        url = captured[0]
        assert "page%5Bsize%5D=1" in url or "page[size]=1" in url
        assert "page%5Bafter%5D=tok-1" in url or "page[after]=tok-1" in url
        assert page.next_cursor == "tok-2"

    def test_empty_response(self):
        def handler(req):
            return httpx.Response(
                200, json={"data": [], "meta": {"page_size": 50}}
            )

        c = _client_with_handler(handler)
        try:
            page = c.resource_types.list()
        finally:
            c._close()
        assert len(page) == 0
        assert page.next_cursor is None
        assert list(page) == []

    def test_unexpected_status_raises(self):
        def handler(req):
            return httpx.Response(500, json={"errors": [{"status": "500"}]})

        c = _client_with_handler(handler)
        try:
            with pytest.raises(UnexpectedStatus):
                c.resource_types.list()
        finally:
            c._close()


# ---------------------------------------------------------------------------
# actions.list
# ---------------------------------------------------------------------------


class TestActionsList:
    def test_unfiltered(self):
        def handler(req):
            url = str(req.url)
            assert "/api/v1/actions" in url
            assert "filter%5Bresource_type%5D" not in url
            assert "filter[resource_type]" not in url
            return httpx.Response(
                200,
                json={
                    "data": [
                        _action_resource(key="account.updated"),
                        _action_resource(key="user.login"),
                    ],
                    "meta": {"page_size": 50},
                },
            )

        c = _client_with_handler(handler)
        try:
            page = c.actions.list()
        finally:
            c._close()
        assert isinstance(page, ActionListPage)
        assert [a.id for a in page] == ["account.updated", "user.login"]

    def test_filter_by_resource_type(self):
        captured_url = []

        def handler(req):
            captured_url.append(str(req.url))
            return httpx.Response(
                200,
                json={
                    "data": [_action_resource(key="user.login")],
                    "meta": {"page_size": 50},
                },
            )

        c = _client_with_handler(handler)
        try:
            page = c.actions.list(filter_resource_type="user")
        finally:
            c._close()
        # Wrapper must have sent the filter on the wire — it's the entire
        # point of the cascading-filter feature.
        url = captured_url[0]
        assert "user" in url
        assert (
            "filter%5Bresource_type%5D=user" in url
            or "filter[resource_type]=user" in url
        )
        assert [a.id for a in page] == ["user.login"]

    def test_pagination_cursor_with_filter_in_next_link(self):
        def handler(req):
            return httpx.Response(
                200,
                json={
                    "data": [_action_resource(key="a.x")],
                    "links": {
                        "next": (
                            "/api/v1/actions?page[size]=1&page[after]=tok-2"
                            "&filter[resource_type]=user"
                        )
                    },
                    "meta": {"page_size": 1},
                },
            )

        c = _client_with_handler(handler)
        try:
            page = c.actions.list(page_size=1, filter_resource_type="user")
        finally:
            c._close()
        # The cursor token is sliced at the next ``&`` so trailing query
        # params don't leak into ``next_cursor``.
        assert page.next_cursor == "tok-2"

    def test_pagination_cursor_extraction_when_no_link(self):
        def handler(req):
            return httpx.Response(
                200,
                json={"data": [], "meta": {"page_size": 50}},
            )

        c = _client_with_handler(handler)
        try:
            page = c.actions.list()
        finally:
            c._close()
        assert page.next_cursor is None

    def test_action_list_page_len_and_iter(self):
        # Direct __len__ check — coverage gate requires every wrapper line.
        page = ActionListPage(
            actions=[
                Action._from_resource(_action_resource(key="a.x")),
                Action._from_resource(_action_resource(key="b.y")),
            ],
            next_cursor=None,
        )
        assert len(page) == 2
        assert [a.id for a in page] == ["a.x", "b.y"]


# ---------------------------------------------------------------------------
# functions.wipe.actions.execute
# ---------------------------------------------------------------------------


class TestWipeAction:
    def test_happy_path(self):
        captured: dict[str, Any] = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["method"] = req.method
            captured["url"] = str(req.url)
            captured["body"] = req.content
            return httpx.Response(
                200,
                json={
                    "wiped": True,
                    "tables": {
                        "audit_event": 100,
                        "audit_event_quota": 5,
                        "forwarder": 1,
                        "forwarder_delivery": 27,
                        "resource_type": 4,
                        "action": 9,
                    },
                    "completed_at": "2026-05-08T19:31:24Z",
                },
            )

        c = _client_with_handler(handler)
        try:
            result = c.functions.wipe.actions.execute()
        finally:
            c._close()
        assert captured["method"] == "POST"
        assert "/api/v1/functions/wipe/actions/execute" in captured["url"]
        # Body is empty per the action contract.
        assert captured["body"] in (b"{}", b"")
        assert result.audit_event == 100
        assert result.total_rows_deleted == 100 + 5 + 1 + 27 + 4 + 9

    def test_unexpected_status_raises(self):
        def handler(req):
            return httpx.Response(401, json={"errors": [{"status": "401"}]})

        c = _client_with_handler(handler)
        try:
            with pytest.raises(UnexpectedStatus):
                c.functions.wipe.actions.execute()
        finally:
            c._close()


# ---------------------------------------------------------------------------
# AsyncAuditClient surface
# ---------------------------------------------------------------------------


def test_async_client_exposes_new_namespaces():
    """The AsyncAuditClient placeholder delegates to AuditClient, so the
    new resource_types / actions / functions.wipe surfaces must appear on
    it too. Without this, async callers couldn't reach the new endpoints
    until full async support lands."""
    from smplkit.audit import AsyncAuditClient

    c = AsyncAuditClient(api_key="sk_api_test", base_url="https://audit.example.com")
    try:
        assert c.resource_types is not None
        assert c.actions is not None
        assert c.functions.wipe is not None
        assert c.functions.wipe.actions is not None
    finally:
        # _close is async; we don't need to await for this synchronous check.
        pass
