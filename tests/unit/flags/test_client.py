"""Tests for FlagsClient and AsyncFlagsClient management methods."""

import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from smplkit._errors import (
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.flags.client import (
    AsyncFlagsClient,
    BoolFlagHandle,
    FlagStats,
    FlagsClient,
    JsonFlagHandle,
    NumberFlagHandle,
    StringFlagHandle,
    _ResolutionCache,
    _evaluate_flag,
)
from smplkit.flags.models import AsyncFlag, Flag
from smplkit.flags.types import Context, FlagType

_TEST_UUID = "5a0c6be1-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _mock_flag_response(*, key="test-flag", name="Test Flag", type_="BOOLEAN", default=False):
    """Build a mock parsed flag response."""
    mock_values = [MagicMock(name="True", value=True), MagicMock(name="False", value=False)]
    mock_values[0].name = "True"
    mock_values[0].value = True
    mock_values[1].name = "False"
    mock_values[1].value = False

    mock_attrs = MagicMock()
    mock_attrs.key = key
    mock_attrs.name = name
    mock_attrs.type_ = type_
    mock_attrs.default = default
    mock_attrs.values = mock_values
    mock_attrs.description = None
    mock_attrs.environments = MagicMock()
    mock_attrs.environments.__class__.__name__ = "Unset"
    mock_attrs.created_at = None
    mock_attrs.updated_at = None

    # Make environments look like Unset
    from smplkit._generated.flags.types import UNSET

    mock_attrs.environments = UNSET

    mock_resource = MagicMock()
    mock_resource.id = _TEST_UUID
    mock_resource.attributes = mock_attrs

    mock_parsed = MagicMock()
    mock_parsed.data = mock_resource

    return mock_parsed


def _mock_list_parsed():
    """Build a mock parsed list response with one flag."""
    mock_parsed = MagicMock()
    mock_parsed.data = [_mock_flag_response().data]
    return mock_parsed


def _ok_response(parsed=None, status=HTTPStatus.OK):
    """Build a mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = b""
    resp.parsed = parsed
    return resp


def _mock_httpx_response(json_data=None, status_code=200):
    """Build a mock httpx response for direct HTTP calls."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b""
    resp.json.return_value = json_data or {}
    return resp


def _ct_json(*, id="ct-1", key="user", name="User", attributes=None):
    """Build a context type JSON:API response dict."""
    return {
        "data": {
            "id": id,
            "attributes": {"key": key, "name": name, "attributes": attributes or {}},
        }
    }


def _ct_list_json(*items):
    """Build a context type list JSON:API response dict."""
    return {
        "data": [
            {"id": f"ct-{i}", "attributes": {"key": item[0], "name": item[1], "attributes": {}}}
            for i, item in enumerate(items)
        ]
    }


def _parsed_ct_response(*, id="ct-1", key="user", name="User", attributes=None):
    """Build a mock parsed ContextTypeResponse from the generated app client."""
    from smplkit._generated.app.models.context_type import ContextType as GenContextType
    from smplkit._generated.app.models.context_type_attributes import ContextTypeAttributes
    from smplkit._generated.app.models.context_type_resource import ContextTypeResource
    from smplkit._generated.app.models.context_type_response import ContextTypeResponse

    ct_attrs = ContextTypeAttributes()
    ct_attrs.additional_properties = dict(attributes or {})
    gen_ct = GenContextType(key=key, name=name, attributes=ct_attrs)
    resource = ContextTypeResource(type_="context_type", attributes=gen_ct, id=id)
    return ContextTypeResponse(data=resource)


def _parsed_ct_list_response(*items):
    """Build a mock parsed ContextTypeListResponse."""
    from smplkit._generated.app.models.context_type import ContextType as GenContextType
    from smplkit._generated.app.models.context_type_attributes import ContextTypeAttributes
    from smplkit._generated.app.models.context_type_list_response import ContextTypeListResponse
    from smplkit._generated.app.models.context_type_resource import ContextTypeResource

    resources = []
    for i, (key, name) in enumerate(items):
        ct_attrs = ContextTypeAttributes()
        gen_ct = GenContextType(key=key, name=name, attributes=ct_attrs)
        resources.append(ContextTypeResource(type_="context_type", attributes=gen_ct, id=f"ct-{i}"))
    return ContextTypeListResponse(data=resources)


def _parsed_context_list_response():
    """Build a mock parsed ContextListResponse with one item."""
    from smplkit._generated.app.models.context import Context as GenContext
    from smplkit._generated.app.models.context_list_response import ContextListResponse
    from smplkit._generated.app.models.context_resource import ContextResource

    ctx = GenContext(name="u-1", context_type="user")
    resource = ContextResource(type_="context", attributes=ctx, id="user:u-1")
    return ContextListResponse(data=[resource])


def _make_flags_client():
    """Create a FlagsClient with a mocked parent."""
    parent = MagicMock()
    parent._api_key = "sk_test"
    with patch("smplkit.flags.client.AuthenticatedClient"):
        client = FlagsClient(parent)
    return client


def _make_async_flags_client():
    """Create an AsyncFlagsClient with a mocked parent."""
    parent = MagicMock()
    parent._api_key = "sk_test"
    with patch("smplkit.flags.client.AuthenticatedClient"):
        client = AsyncFlagsClient(parent)
    return client


def _make_mock_flag(client):
    """Create a Flag model for use in _update_flag tests."""
    return Flag(
        client,
        id=_TEST_UUID,
        key="test-flag",
        name="Test Flag",
        type="BOOLEAN",
        default=False,
        values=[{"name": "True", "value": True}, {"name": "False", "value": False}],
    )


def _make_mock_async_flag(client):
    """Create an AsyncFlag model for use in _update_flag tests."""
    return AsyncFlag(
        client,
        id=_TEST_UUID,
        key="test-flag",
        name="Test Flag",
        type="BOOLEAN",
        default=False,
        values=[{"name": "True", "value": True}, {"name": "False", "value": False}],
    )


def _setup_httpx_mock(client, method="get"):
    """Set up a mock httpx client on a FlagsClient. Returns the mock method."""
    mock_httpx = MagicMock()
    mock_method = getattr(mock_httpx, method)
    client._flags_http.get_httpx_client = MagicMock(return_value=mock_httpx)
    return mock_method


def _setup_async_httpx_mock(client, method="get"):
    """Set up a mock async httpx client on an AsyncFlagsClient. Returns the mock method."""
    mock_httpx = MagicMock()
    mock_method = AsyncMock()
    setattr(mock_httpx, method, mock_method)
    client._flags_http.get_async_httpx_client = MagicMock(return_value=mock_httpx)
    return mock_method


# ---------------------------------------------------------------------------
# _ResolutionCache
# ---------------------------------------------------------------------------


class TestResolutionCache:
    def test_put_update_existing_key(self):
        cache = _ResolutionCache(max_size=5)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)
        hit, val = cache.get("a")
        assert hit is True
        assert val == 10

    def test_put_evicts_oldest_when_full(self):
        cache = _ResolutionCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        hit_a, _ = cache.get("a")
        assert hit_a is False
        hit_c, val_c = cache.get("c")
        assert hit_c is True
        assert val_c == 3


# ---------------------------------------------------------------------------
# FlagStats
# ---------------------------------------------------------------------------


class TestFlagStats:
    def test_repr(self):
        stats = FlagStats(cache_hits=5, cache_misses=3)
        assert repr(stats) == "FlagStats(cache_hits=5, cache_misses=3)"


# ---------------------------------------------------------------------------
# Typed flag handles
# ---------------------------------------------------------------------------


class TestTypedFlagHandles:
    def _make_handle(self, cls, default, evaluate_returns):
        ns = MagicMock()
        ns._evaluate_handle = MagicMock(return_value=evaluate_returns)
        return cls(ns, "flag-key", default)

    def test_bool_handle_returns_bool(self):
        h = self._make_handle(BoolFlagHandle, False, True)
        assert h.get() is True

    def test_bool_handle_wrong_type_returns_default(self):
        h = self._make_handle(BoolFlagHandle, False, "not-a-bool")
        assert h.get() is False

    def test_string_handle_returns_string(self):
        h = self._make_handle(StringFlagHandle, "default", "hello")
        assert h.get() == "hello"

    def test_string_handle_wrong_type_returns_default(self):
        h = self._make_handle(StringFlagHandle, "default", 123)
        assert h.get() == "default"

    def test_number_handle_returns_int(self):
        h = self._make_handle(NumberFlagHandle, 0, 42)
        assert h.get() == 42

    def test_number_handle_returns_float(self):
        h = self._make_handle(NumberFlagHandle, 0.0, 3.14)
        assert h.get() == 3.14

    def test_number_handle_rejects_bool(self):
        h = self._make_handle(NumberFlagHandle, 0, True)
        assert h.get() == 0

    def test_number_handle_wrong_type_returns_default(self):
        h = self._make_handle(NumberFlagHandle, 0, "not-a-number")
        assert h.get() == 0

    def test_json_handle_returns_dict(self):
        h = self._make_handle(JsonFlagHandle, {}, {"a": 1})
        assert h.get() == {"a": 1}

    def test_json_handle_wrong_type_returns_default(self):
        h = self._make_handle(JsonFlagHandle, {"fallback": True}, "not-a-dict")
        assert h.get() == {"fallback": True}


# ---------------------------------------------------------------------------
# _evaluate_flag (module-level function)
# ---------------------------------------------------------------------------


class TestEvaluateFlag:
    def test_disabled_environment_returns_fallback(self):
        flag_def = {
            "default": "global-default",
            "environments": {
                "staging": {"enabled": False, "default": "staging-default", "rules": []},
            },
        }
        result = _evaluate_flag(flag_def, "staging", {})
        assert result == "staging-default"

    def test_disabled_environment_no_env_default_returns_flag_default(self):
        flag_def = {
            "default": "global-default",
            "environments": {
                "staging": {"enabled": False, "rules": []},
            },
        }
        result = _evaluate_flag(flag_def, "staging", {})
        assert result == "global-default"


# ---------------------------------------------------------------------------
# Sync FlagsClient: CRUD
# ---------------------------------------------------------------------------


class TestFlagsClient:
    def test_init(self):
        client = SmplClient(api_key="sk_test", environment="test")
        assert isinstance(client.flags, FlagsClient)

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create(self, mock_create):
        mock_create.return_value = _ok_response(parsed=_mock_flag_response(), status=HTTPStatus.CREATED)
        client = SmplClient(api_key="sk_test", environment="test")
        flag = client.flags.create("test-flag", name="Test Flag", type=FlagType.BOOLEAN, default=False)
        assert flag.key == "test-flag"
        assert flag.id == _TEST_UUID

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_auto_boolean_values(self, mock_create):
        mock_create.return_value = _ok_response(parsed=_mock_flag_response(), status=HTTPStatus.CREATED)
        client = SmplClient(api_key="sk_test", environment="test")
        client.flags.create("test-flag", name="Test", type=FlagType.BOOLEAN, default=False)
        call_kwargs = mock_create.call_args
        body = call_kwargs.kwargs["body"]
        values = body.data.attributes.values
        assert len(values) == 2

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_parsed_none_raises(self, mock_create):
        mock_create.return_value = _ok_response(parsed=None, status=HTTPStatus.CREATED)
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplValidationError):
            client.flags.create("test-flag", name="Test", type=FlagType.BOOLEAN, default=False)

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get(self, mock_get):
        mock_get.return_value = _ok_response(parsed=_mock_flag_response())
        client = SmplClient(api_key="sk_test", environment="test")
        flag = client.flags.get(_TEST_UUID)
        assert flag.key == "test-flag"

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_404(self, mock_get):
        mock_get.return_value = _ok_response(parsed=None, status=HTTPStatus.NOT_FOUND)
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotFoundError):
            client.flags.get(_TEST_UUID)

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_parsed_none(self, mock_get):
        mock_get.return_value = _ok_response(parsed=None)
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotFoundError):
            client.flags.get(_TEST_UUID)

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = SmplClient(api_key="sk_test", environment="test")
        flags = client.flags.list()
        assert len(flags) == 1
        assert flags[0].key == "test-flag"

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list_empty(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)
        client = SmplClient(api_key="sk_test", environment="test")
        flags = client.flags.list()
        assert flags == []

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)
        client = SmplClient(api_key="sk_test", environment="test")
        client.flags.delete(_TEST_UUID)

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("connection refused")
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplConnectionError):
            client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_timeout(self, mock_get):
        mock_get.side_effect = httpx.ReadTimeout("timed out")
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplTimeoutError):
            client.flags.get(_TEST_UUID)

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_generic_exception(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(RuntimeError):
            client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_generic_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(RuntimeError):
            client.flags.get(_TEST_UUID)

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(RuntimeError):
            client.flags.list()

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete_generic_exception(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(RuntimeError):
            client.flags.delete(_TEST_UUID)


# ---------------------------------------------------------------------------
# Sync FlagsClient: _update_flag
# ---------------------------------------------------------------------------


class TestFlagsClientUpdateFlag:
    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_success(self, mock_update):
        mock_update.return_value = _ok_response(parsed=_mock_flag_response())
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        result = client._update_flag(flag=flag)
        assert result.key == "test-flag"

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_with_overrides(self, mock_update):
        mock_update.return_value = _ok_response(parsed=_mock_flag_response())
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        result = client._update_flag(
            flag=flag,
            name="New Name",
            default=True,
            description="Updated",
            values=[{"name": "A", "value": 1}],
            environments={"prod": {"enabled": True, "default": False, "rules": []}},
        )
        assert result.key == "test-flag"

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_parsed_none_raises(self, mock_update):
        mock_update.return_value = _ok_response(parsed=None)
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        with pytest.raises(SmplValidationError):
            client._update_flag(flag=flag)

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        with pytest.raises(SmplConnectionError):
            client._update_flag(flag=flag)

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_generic_exception(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        with pytest.raises(RuntimeError):
            client._update_flag(flag=flag)


# ---------------------------------------------------------------------------
# Sync FlagsClient: Context type CRUD
# ---------------------------------------------------------------------------


class TestFlagsClientContextTypes:
    @patch("smplkit.flags.client.gen_create_context_type.sync_detailed")
    def test_create_context_type(self, mock_create):
        mock_create.return_value = _ok_response(parsed=_parsed_ct_response())
        client = _make_flags_client()
        ct = client.create_context_type("user", name="User")
        assert ct.key == "user"
        assert ct.name == "User"
        mock_create.assert_called_once()

    @patch("smplkit.flags.client.gen_update_context_type.sync_detailed")
    def test_update_context_type(self, mock_update):
        mock_update.return_value = _ok_response(parsed=_parsed_ct_response(attributes={"plan": {}}))
        client = _make_flags_client()
        ct = client.update_context_type(_TEST_UUID, key="user", name="User", attributes={"plan": {}})
        assert ct.key == "user"

    @patch("smplkit.flags.client.gen_list_context_types.sync_detailed")
    def test_list_context_types(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_parsed_ct_list_response(("user", "User"), ("device", "Device")))
        client = _make_flags_client()
        result = client.list_context_types()
        assert len(result) == 2
        assert result[0].key == "user"

    @patch("smplkit.flags.client.gen_delete_context_type.sync_detailed")
    def test_delete_context_type(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)
        client = _make_flags_client()
        client.delete_context_type(_TEST_UUID)
        mock_delete.assert_called_once()

    @patch("smplkit.flags.client.gen_list_contexts.sync_detailed")
    def test_list_contexts(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_parsed_context_list_response())
        client = _make_flags_client()
        result = client.list_contexts(context_type_key="user")
        assert len(result) == 1
        mock_list.assert_called_once()
        # Verify the filter param was passed via the generated function
        _, kwargs = mock_list.call_args
        assert kwargs["filtercontext_type_id"] == "user"

    # Error paths for coverage

    @patch("smplkit.flags.client.gen_create_context_type.sync_detailed")
    def test_create_context_type_network_error(self, mock_create):
        mock_create.side_effect = httpx.TimeoutException("timeout")
        client = _make_flags_client()
        with pytest.raises(SmplTimeoutError):
            client.create_context_type("user", name="User")

    @patch("smplkit.flags.client.gen_update_context_type.sync_detailed")
    def test_update_context_type_network_error(self, mock_update):
        mock_update.side_effect = httpx.TimeoutException("timeout")
        client = _make_flags_client()
        with pytest.raises(SmplTimeoutError):
            client.update_context_type(_TEST_UUID, key="user", name="User", attributes={})

    @patch("smplkit.flags.client.gen_list_context_types.sync_detailed")
    def test_list_context_types_network_error(self, mock_list):
        mock_list.side_effect = httpx.TimeoutException("timeout")
        client = _make_flags_client()
        with pytest.raises(SmplTimeoutError):
            client.list_context_types()

    @patch("smplkit.flags.client.gen_delete_context_type.sync_detailed")
    def test_delete_context_type_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.TimeoutException("timeout")
        client = _make_flags_client()
        with pytest.raises(SmplTimeoutError):
            client.delete_context_type(_TEST_UUID)

    @patch("smplkit.flags.client.gen_list_contexts.sync_detailed")
    def test_list_contexts_network_error(self, mock_list):
        mock_list.side_effect = httpx.TimeoutException("timeout")
        client = _make_flags_client()
        with pytest.raises(SmplTimeoutError):
            client.list_contexts(context_type_key="user")

    # Non-network errors propagate as-is (bare raise path)

    @patch("smplkit.flags.client.gen_create_context_type.sync_detailed")
    def test_create_context_type_other_error(self, mock_create):
        mock_create.side_effect = RuntimeError("boom")
        client = _make_flags_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.create_context_type("user", name="User")

    @patch("smplkit.flags.client.gen_update_context_type.sync_detailed")
    def test_update_context_type_other_error(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        client = _make_flags_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.update_context_type(_TEST_UUID, key="user", name="User", attributes={})

    @patch("smplkit.flags.client.gen_list_context_types.sync_detailed")
    def test_list_context_types_other_error(self, mock_list):
        mock_list.side_effect = RuntimeError("boom")
        client = _make_flags_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.list_context_types()

    @patch("smplkit.flags.client.gen_delete_context_type.sync_detailed")
    def test_delete_context_type_other_error(self, mock_delete):
        mock_delete.side_effect = RuntimeError("boom")
        client = _make_flags_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.delete_context_type(_TEST_UUID)

    @patch("smplkit.flags.client.gen_list_contexts.sync_detailed")
    def test_list_contexts_other_error(self, mock_list):
        mock_list.side_effect = RuntimeError("boom")
        client = _make_flags_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.list_contexts(context_type_key="user")

    # parsed=None paths

    @patch("smplkit.flags.client.gen_create_context_type.sync_detailed")
    def test_create_context_type_parsed_none(self, mock_create):
        mock_create.return_value = _ok_response(parsed=None)
        client = _make_flags_client()
        with pytest.raises(SmplValidationError):
            client.create_context_type("user", name="User")

    @patch("smplkit.flags.client.gen_update_context_type.sync_detailed")
    def test_update_context_type_parsed_none(self, mock_update):
        mock_update.return_value = _ok_response(parsed=None)
        client = _make_flags_client()
        with pytest.raises(SmplValidationError):
            client.update_context_type(_TEST_UUID, key="user", name="User", attributes={})

    @patch("smplkit.flags.client.gen_list_context_types.sync_detailed")
    def test_list_context_types_parsed_none(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)
        client = _make_flags_client()
        with pytest.raises(SmplValidationError):
            client.list_context_types()

    @patch("smplkit.flags.client.gen_list_contexts.sync_detailed")
    def test_list_contexts_parsed_none(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)
        client = _make_flags_client()
        result = client.list_contexts(context_type_key="user")
        assert result == []


# ---------------------------------------------------------------------------
# Sync FlagsClient: Connect / Disconnect / Refresh
# ---------------------------------------------------------------------------


class TestFlagsClientLifecycle:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_connect_internal(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        client._parent._environment = "staging"
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws

        client._connect_internal()

        assert client._connected is True
        assert client._environment == "staging"
        assert client._ws_manager is mock_ws
        assert mock_ws.on.call_count == 2
        assert "test-flag" in client._flag_store

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_disconnect_with_ws(self, mock_list, mock_bulk):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        mock_bulk.return_value = _ok_response()
        client = _make_flags_client()
        client._parent._environment = "staging"
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws
        client._connect_internal()

        client.disconnect()

        assert client._connected is False
        assert client._environment is None
        assert client._ws_manager is None
        assert mock_ws.off.call_count == 2
        assert client._flag_store == {}

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_disconnect_without_ws(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_flags_client()
        client._ws_manager = None
        client.disconnect()
        assert client._connected is False

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_refresh(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        client._connected = True
        client._environment = "prod"
        listener = MagicMock()
        client._global_listeners.append(listener)

        # Pre-populate store so fire_change_listeners_all has something to iterate
        client._flag_store = {"old-flag": {"key": "old-flag"}}
        client.refresh()

        assert "test-flag" in client._flag_store
        assert listener.called

    def test_connection_status_disconnected(self):
        client = _make_flags_client()
        assert client.connection_status() == "disconnected"

    def test_connection_status_connected(self):
        client = _make_flags_client()
        mock_ws = MagicMock()
        mock_ws.connection_status = "connected"
        client._ws_manager = mock_ws
        assert client.connection_status() == "connected"

    def test_stats(self):
        client = _make_flags_client()
        stats = client.stats()
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0


# ---------------------------------------------------------------------------
# Sync FlagsClient: Flush contexts
# ---------------------------------------------------------------------------


class TestFlagsClientFlush:
    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_with_pending(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_flags_client()
        client.register(Context("user", "u-1", plan="enterprise"))

        client.flush_contexts()

        mock_bulk.assert_called_once()
        _, kwargs = mock_bulk.call_args
        body = kwargs["body"]
        assert body.contexts[0].type_ == "user"
        assert body.contexts[0].key == "u-1"

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_empty_batch(self, mock_bulk):
        client = _make_flags_client()

        client.flush_contexts()

        mock_bulk.assert_not_called()

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_exception_swallowed(self, mock_bulk):
        mock_bulk.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        client.register(Context("user", "u-1"))

        # Should not raise
        client.flush_contexts()


# ---------------------------------------------------------------------------
# Sync FlagsClient: Evaluate
# ---------------------------------------------------------------------------


class TestFlagsClientEvaluate:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_evaluate_connected_uses_store(self, mock_list):
        client = _make_flags_client()
        client._connected = True
        client._flag_store = {
            "my-flag": {
                "key": "my-flag",
                "default": "off",
                "environments": {"prod": {"enabled": True, "default": "env-default", "rules": []}},
            }
        }
        result = client.evaluate("my-flag", environment="prod", context=[Context("user", "u-1")])
        assert result == "env-default"
        mock_list.assert_not_called()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_evaluate_not_connected_fetches(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        client._connected = False
        result = client.evaluate("test-flag", environment="prod", context=[Context("user", "u-1")])
        # Flag exists but "prod" env not configured, returns flag default
        assert result is False
        mock_list.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_evaluate_flag_not_found(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        result = client.evaluate("nonexistent", environment="prod", context=[Context("user", "u-1")])
        assert result is None


class TestFlagsClientEvaluateHandle:
    def test_not_connected_raises(self):
        from smplkit._errors import SmplNotConnectedError

        client = _make_flags_client()
        client._connected = False
        with pytest.raises(SmplNotConnectedError, match="not connected"):
            client._evaluate_handle("key", "default_val", None)

    def test_with_explicit_context(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": False,
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True}],
                    },
                },
            }
        }
        result = client._evaluate_handle("flag-a", False, [Context("user", "u-1", plan="enterprise")])
        assert result is True

    def test_with_context_provider(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": "off",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        client._context_provider = lambda: [Context("user", "u-1", plan="free")]

        result = client._evaluate_handle("flag-a", "off", None)
        # Env default not set, falls through to flag default (rules empty, no match)
        assert result == "off"
        # Contexts should have been observed
        assert client._context_buffer.pending_count > 0

    @patch("smplkit.flags.client.threading.Thread")
    def test_context_provider_triggers_flush(self, mock_thread):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {"flag-a": {"key": "flag-a", "default": False, "environments": {}}}

        # Fill the buffer to trigger flush
        for i in range(100):
            client._context_buffer.observe([Context("user", f"u-{i}")])

        client._context_provider = lambda: [Context("user", "trigger")]
        client._evaluate_handle("flag-a", False, None)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    def test_no_provider_empty_context(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": "fallback",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        client._context_provider = None
        result = client._evaluate_handle("flag-a", "fallback", None)
        assert result == "fallback"

    def test_flag_not_in_store(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {}
        result = client._evaluate_handle("missing", "default_val", [Context("user", "u-1")])
        assert result == "default_val"

    def test_evaluate_none_becomes_default(self):
        """When _evaluate_flag returns None, _evaluate_handle should return default."""
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        # Flag with no environment match returns None from _evaluate_flag
        client._flag_store = {"flag-a": {"key": "flag-a", "default": None, "environments": {}}}
        result = client._evaluate_handle("flag-a", "my-default", [Context("user", "u-1")])
        assert result == "my-default"

    def test_cache_hit(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": "val",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        ctx = [Context("user", "u-1")]

        # First call - miss
        client._evaluate_handle("flag-a", "val", ctx)
        # Second call - hit
        result = client._evaluate_handle("flag-a", "val", ctx)
        assert result == "val"
        assert client._cache.cache_hits == 1
        assert client._cache.cache_misses == 1


# ---------------------------------------------------------------------------
# Sync FlagsClient: Event handlers + listeners
# ---------------------------------------------------------------------------


class TestFlagsClientEventHandlers:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)

        client._handle_flag_changed({"key": "test-flag"})

        mock_list.assert_called_once()
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)

        client._handle_flag_deleted({"key": "test-flag"})

        mock_list.assert_called_once()
        listener.assert_called_once()


class TestFlagsClientChangeListeners:
    def test_fire_global_and_handle_listeners(self):
        client = _make_flags_client()
        global_listener = MagicMock()
        handle_listener = MagicMock()
        client._global_listeners.append(global_listener)
        handle = client.boolFlag("my-flag", False)
        handle.on_change(handle_listener)

        client._fire_change_listeners("my-flag", "websocket")

        global_listener.assert_called_once()
        handle_listener.assert_called_once()

    def test_global_listener_exception_swallowed(self):
        client = _make_flags_client()
        bad_listener = MagicMock(side_effect=RuntimeError("boom"))
        good_listener = MagicMock()
        client._global_listeners.extend([bad_listener, good_listener])

        client._fire_change_listeners("flag-a", "websocket")

        bad_listener.assert_called_once()
        good_listener.assert_called_once()

    def test_handle_listener_exception_swallowed(self):
        client = _make_flags_client()
        handle = client.boolFlag("my-flag", False)
        bad_listener = MagicMock(side_effect=RuntimeError("boom"))
        handle.on_change(bad_listener)

        # Should not raise
        client._fire_change_listeners("my-flag", "websocket")

    def test_none_key_fires_nothing(self):
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._fire_change_listeners(None, "websocket")
        listener.assert_not_called()

    def test_fire_change_listeners_all(self):
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._flag_store = {"flag-a": {"key": "flag-a"}, "flag-b": {"key": "flag-b"}}

        client._fire_change_listeners_all("manual")

        assert listener.call_count == 2


# ---------------------------------------------------------------------------
# Sync FlagsClient: Model conversion + _parse_context_type
# ---------------------------------------------------------------------------


class TestFlagsClientModelConversion:
    def test_to_model(self):
        client = _make_flags_client()
        parsed = _mock_flag_response()
        result = client._to_model(parsed)
        assert isinstance(result, Flag)
        assert result.key == "test-flag"

    def test_resource_to_model(self):
        client = _make_flags_client()
        resource = _mock_flag_response().data
        result = client._resource_to_model(resource)
        assert isinstance(result, Flag)
        assert result.id == _TEST_UUID
        assert result.key == "test-flag"
        assert result.name == "Test Flag"

    def test_parse_gen_context_type_response(self):
        """The module-level _parse_gen_context_type_response works correctly."""
        from smplkit.flags.client import _parse_gen_context_type_response

        parsed = _parsed_ct_response(id="ct-1", key="user", name="User", attributes={"plan": {}})
        ct = _parse_gen_context_type_response(parsed)
        assert ct.key == "user"
        assert ct.name == "User"
        assert ct.attributes == {"plan": {}}


# ---------------------------------------------------------------------------
# Sync FlagsClient: Fetch internals
# ---------------------------------------------------------------------------


class TestFlagsClientFetchInternals:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_all_flags(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        client._fetch_all_flags()
        assert "test-flag" in client._flag_store

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_flags_client()
        result = client._fetch_flags_list()
        assert len(result) == 1
        assert result[0]["key"] == "test-flag"

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list_empty(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)
        client = _make_flags_client()
        result = client._fetch_flags_list()
        assert result == []

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client._fetch_flags_list()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        with pytest.raises(RuntimeError):
            client._fetch_flags_list()


# ---------------------------------------------------------------------------
# Sync FlagsClient: Runtime (misc already tested in TestFlagsRuntime)
# ---------------------------------------------------------------------------


class TestFlagsRuntime:
    """Test runtime behavior with mocked flag store."""

    def test_flag_handles_raise_before_connect(self):
        from smplkit._errors import SmplNotConnectedError

        client = SmplClient(api_key="sk_test", environment="test")
        handle = client.flags.boolFlag("test", False)
        with pytest.raises(SmplNotConnectedError, match="not connected"):
            handle.get()

    def test_stats_initial(self):
        client = SmplClient(api_key="sk_test", environment="test")
        stats = client.flags.stats()
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

    def test_connection_status_initial(self):
        client = SmplClient(api_key="sk_test", environment="test")
        assert client.flags.connection_status() == "disconnected"

    def test_context_provider_decorator(self):
        client = SmplClient(api_key="sk_test", environment="test")

        @client.flags.context_provider
        def provider():
            return [Context("user", "u-1")]

        assert client.flags._context_provider is provider

    def test_on_change_decorator(self):
        client = SmplClient(api_key="sk_test", environment="test")

        @client.flags.on_change
        def listener(event):
            pass

        assert len(client.flags._global_listeners) == 1

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_evaluate_handle_with_connected_store(self, mock_list):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns._connected = True
        ns._environment = "staging"
        ns._flag_store = {
            "checkout-v2": {
                "key": "checkout-v2",
                "name": "Checkout V2",
                "type": "BOOLEAN",
                "default": False,
                "values": [],
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [
                            {"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True},
                        ],
                    },
                },
            },
        }
        handle = ns.boolFlag("checkout-v2", False)
        result = handle.get(context=[Context("user", "u-1", plan="enterprise")])
        assert result is True
        result = handle.get(context=[Context("user", "u-2", plan="free")])
        assert result is False

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_cache_hits_on_repeated_evaluation(self, mock_list):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns._connected = True
        ns._environment = "staging"
        ns._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "type": "BOOLEAN",
                "default": False,
                "environments": {"staging": {"enabled": True, "rules": []}},
            },
        }
        handle = ns.boolFlag("flag-a", False)
        ctx = [Context("user", "u-1", plan="free")]
        handle.get(context=ctx)
        handle.get(context=ctx)
        handle.get(context=ctx)
        stats = ns.stats()
        assert stats.cache_misses == 1
        assert stats.cache_hits == 2

    def test_cache_cleared_on_change(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns._cache.put("k", "v")
        ns._cache.clear()
        hit, _ = ns._cache.get("k")
        assert hit is False


# ---------------------------------------------------------------------------
# Sync FlagsClient: Register
# ---------------------------------------------------------------------------


class TestRegister:
    def test_register_single_context(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns.register(Context("user", "u-1", plan="enterprise"))
        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["type"] == "user"
        assert batch[0]["key"] == "u-1"
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_register_single_context_with_name(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns.register(Context("user", "u-1", name="Alice Smith", plan="enterprise"))
        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["type"] == "user"
        assert batch[0]["key"] == "u-1"
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_register_list_of_contexts(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns.register([Context("user", "u-1", plan="enterprise"), Context("account", "acme-corp", region="us")])
        batch = ns._context_buffer.drain()
        assert len(batch) == 2
        assert batch[0]["type"] == "user"
        assert batch[0]["key"] == "u-1"
        assert batch[1]["type"] == "account"
        assert batch[1]["key"] == "acme-corp"

    def test_register_before_connect(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        assert not ns._connected
        ns.register(Context("user", "u-1", plan="free"))
        ns.register(Context("account", "small-biz", region="eu"))
        batch = ns._context_buffer.drain()
        assert len(batch) == 2

    def test_register_deduplication(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns.register(Context("user", "u-1", plan="enterprise"))
        ns.register(Context("user", "u-1", plan="free"))
        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_register_different_keys_not_deduplicated(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns.register(Context("user", "u-1", plan="enterprise"))
        ns.register(Context("user", "u-2", plan="free"))
        batch = ns._context_buffer.drain()
        assert len(batch) == 2

    def test_register_integrates_with_flush(self):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns.register(Context("user", "u-1", plan="enterprise"))
        ns._context_buffer.observe([Context("account", "acme-corp", region="us")])
        batch = ns._context_buffer.drain()
        assert len(batch) == 2
        keys = {(b["type"], b["key"]) for b in batch}
        assert keys == {("user", "u-1"), ("account", "acme-corp")}


# ===========================================================================
# AsyncFlagsClient tests
# ===========================================================================


class TestAsyncFlagsClient:
    def test_init(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test")
        assert isinstance(client.flags, AsyncFlagsClient)

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create(self, mock_create):
        mock_create.return_value = _ok_response(parsed=_mock_flag_response(), status=HTTPStatus.CREATED)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            flag = await client.flags.create("test-flag", name="Test Flag", type=FlagType.BOOLEAN, default=False)
            assert flag.key == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_auto_boolean_values(self, mock_create):
        mock_create.return_value = _ok_response(parsed=_mock_flag_response(), status=HTTPStatus.CREATED)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            await client.flags.create("test-flag", name="Test", type=FlagType.BOOLEAN, default=False)
            body = mock_create.call_args.kwargs["body"]
            assert len(body.data.attributes.values) == 2

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_parsed_none_raises(self, mock_create):
        mock_create.return_value = _ok_response(parsed=None, status=HTTPStatus.CREATED)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(SmplValidationError):
                await client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get(self, mock_get):
        mock_get.return_value = _ok_response(parsed=_mock_flag_response())

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            flag = await client.flags.get(_TEST_UUID)
            assert flag.key == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_404(self, mock_get):
        mock_get.return_value = _ok_response(parsed=None, status=HTTPStatus.NOT_FOUND)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(SmplNotFoundError):
                await client.flags.get(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_parsed_none(self, mock_get):
        mock_get.return_value = _ok_response(parsed=None)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(SmplNotFoundError):
                await client.flags.get(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            flags = await client.flags.list()
            assert len(flags) == 1

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list_empty(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            flags = await client.flags.list()
            assert flags == []

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            await client.flags.delete(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(SmplConnectionError):
                await client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_generic_exception(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(RuntimeError):
                await client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_generic_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(RuntimeError):
                await client.flags.get(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(RuntimeError):
                await client.flags.list()

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete_generic_exception(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test")
            with pytest.raises(RuntimeError):
                await client.flags.delete(_TEST_UUID)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Async FlagsClient: _update_flag
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientUpdateFlag:
    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_success(self, mock_update):
        mock_update.return_value = _ok_response(parsed=_mock_flag_response())

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            result = await client._update_flag(flag=flag)
            assert result.key == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_with_overrides(self, mock_update):
        mock_update.return_value = _ok_response(parsed=_mock_flag_response())

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            result = await client._update_flag(
                flag=flag,
                name="New Name",
                default=True,
                description="Updated",
                values=[{"name": "A", "value": 1}],
                environments={"prod": {"enabled": True, "default": False, "rules": []}},
            )
            assert result.key == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_parsed_none_raises(self, mock_update):
        mock_update.return_value = _ok_response(parsed=None)

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            with pytest.raises(SmplValidationError):
                await client._update_flag(flag=flag)

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            with pytest.raises(SmplConnectionError):
                await client._update_flag(flag=flag)

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_generic_exception(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            with pytest.raises(RuntimeError):
                await client._update_flag(flag=flag)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Async FlagsClient: Context type CRUD
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientContextTypes:
    @patch("smplkit.flags.client.gen_create_context_type.asyncio_detailed")
    def test_create_context_type(self, mock_create):
        mock_create.return_value = _ok_response(parsed=_parsed_ct_response())

        async def _run():
            client = _make_async_flags_client()
            ct = await client.create_context_type("user", name="User")
            assert ct.key == "user"

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_update_context_type.asyncio_detailed")
    def test_update_context_type(self, mock_update):
        mock_update.return_value = _ok_response(parsed=_parsed_ct_response(attributes={"plan": {}}))

        async def _run():
            client = _make_async_flags_client()
            ct = await client.update_context_type(_TEST_UUID, key="user", name="User", attributes={"plan": {}})
            assert ct.key == "user"

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_context_types.asyncio_detailed")
    def test_list_context_types(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_parsed_ct_list_response(("user", "User"), ("device", "Device")))

        async def _run():
            client = _make_async_flags_client()
            result = await client.list_context_types()
            assert len(result) == 2

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_delete_context_type.asyncio_detailed")
    def test_delete_context_type(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        async def _run():
            client = _make_async_flags_client()
            await client.delete_context_type(_TEST_UUID)
            mock_delete.assert_called_once()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_contexts.asyncio_detailed")
    def test_list_contexts(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_parsed_context_list_response())

        async def _run():
            client = _make_async_flags_client()
            result = await client.list_contexts(context_type_key="user")
            assert len(result) == 1

        asyncio.run(_run())

    # Error paths for coverage

    @patch("smplkit.flags.client.gen_create_context_type.asyncio_detailed")
    def test_create_context_type_network_error(self, mock_create):
        mock_create.side_effect = httpx.TimeoutException("timeout")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplTimeoutError):
                await client.create_context_type("user", name="User")

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_update_context_type.asyncio_detailed")
    def test_update_context_type_network_error(self, mock_update):
        mock_update.side_effect = httpx.TimeoutException("timeout")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplTimeoutError):
                await client.update_context_type(_TEST_UUID, key="user", name="User", attributes={})

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_context_types.asyncio_detailed")
    def test_list_context_types_network_error(self, mock_list):
        mock_list.side_effect = httpx.TimeoutException("timeout")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplTimeoutError):
                await client.list_context_types()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_delete_context_type.asyncio_detailed")
    def test_delete_context_type_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.TimeoutException("timeout")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplTimeoutError):
                await client.delete_context_type(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_contexts.asyncio_detailed")
    def test_list_contexts_network_error(self, mock_list):
        mock_list.side_effect = httpx.TimeoutException("timeout")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplTimeoutError):
                await client.list_contexts(context_type_key="user")

        asyncio.run(_run())

    # Non-network errors propagate as-is (bare raise path)

    @patch("smplkit.flags.client.gen_create_context_type.asyncio_detailed")
    def test_create_context_type_other_error(self, mock_create):
        mock_create.side_effect = RuntimeError("boom")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError, match="boom"):
                await client.create_context_type("user", name="User")

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_update_context_type.asyncio_detailed")
    def test_update_context_type_other_error(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError, match="boom"):
                await client.update_context_type(_TEST_UUID, key="user", name="User", attributes={})

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_context_types.asyncio_detailed")
    def test_list_context_types_other_error(self, mock_list):
        mock_list.side_effect = RuntimeError("boom")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError, match="boom"):
                await client.list_context_types()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_delete_context_type.asyncio_detailed")
    def test_delete_context_type_other_error(self, mock_delete):
        mock_delete.side_effect = RuntimeError("boom")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError, match="boom"):
                await client.delete_context_type(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_contexts.asyncio_detailed")
    def test_list_contexts_other_error(self, mock_list):
        mock_list.side_effect = RuntimeError("boom")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError, match="boom"):
                await client.list_contexts(context_type_key="user")

        asyncio.run(_run())

    # parsed=None paths

    @patch("smplkit.flags.client.gen_create_context_type.asyncio_detailed")
    def test_create_context_type_parsed_none(self, mock_create):
        mock_create.return_value = _ok_response(parsed=None)

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplValidationError):
                await client.create_context_type("user", name="User")

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_update_context_type.asyncio_detailed")
    def test_update_context_type_parsed_none(self, mock_update):
        mock_update.return_value = _ok_response(parsed=None)

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplValidationError):
                await client.update_context_type(_TEST_UUID, key="user", name="User", attributes={})

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_context_types.asyncio_detailed")
    def test_list_context_types_parsed_none(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplValidationError):
                await client.list_context_types()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_list_contexts.asyncio_detailed")
    def test_list_contexts_parsed_none(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)

        async def _run():
            client = _make_async_flags_client()
            result = await client.list_contexts(context_type_key="user")
            assert result == []

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Async FlagsClient: Lifecycle
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientLifecycle:
    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_connect_internal(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = _make_async_flags_client()
            client._parent._environment = "staging"
            mock_ws = MagicMock()
            client._parent._ensure_ws.return_value = mock_ws
            await client._connect_internal()
            assert client._connected is True
            assert client._environment == "staging"
            assert client._ws_manager is mock_ws
            assert mock_ws.on.call_count == 2

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_disconnect_with_ws(self, mock_list, mock_bulk):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        mock_bulk.return_value = _ok_response()

        async def _run():
            client = _make_async_flags_client()
            client._parent._environment = "staging"
            mock_ws = MagicMock()
            client._parent._ensure_ws.return_value = mock_ws
            await client._connect_internal()

            await client.disconnect()

            assert client._connected is False
            assert client._ws_manager is None
            assert mock_ws.off.call_count == 2

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_disconnect_without_ws(self, mock_bulk):
        mock_bulk.return_value = _ok_response()

        async def _run():
            client = _make_async_flags_client()
            await client.disconnect()
            assert client._connected is False

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_refresh(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = _make_async_flags_client()
            client._connected = True
            client._flag_store = {"old-flag": {"key": "old-flag"}}
            listener = MagicMock()
            client._global_listeners.append(listener)
            await client.refresh()
            assert "test-flag" in client._flag_store
            assert listener.called

        asyncio.run(_run())

    def test_connection_status_disconnected(self):
        client = _make_async_flags_client()
        assert client.connection_status() == "disconnected"

    def test_connection_status_connected(self):
        client = _make_async_flags_client()
        mock_ws = MagicMock()
        mock_ws.connection_status = "connected"
        client._ws_manager = mock_ws
        assert client.connection_status() == "connected"

    def test_stats(self):
        client = _make_async_flags_client()
        stats = client.stats()
        assert stats.cache_hits == 0


# ---------------------------------------------------------------------------
# Async FlagsClient: Flush
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientFlush:
    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_flush_with_pending(self, mock_bulk):
        mock_bulk.return_value = _ok_response()

        async def _run():
            client = _make_async_flags_client()
            client.register(Context("user", "u-1", plan="enterprise"))
            await client.flush_contexts()
            mock_bulk.assert_called_once()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_flush_empty_batch(self, mock_bulk):
        async def _run():
            client = _make_async_flags_client()
            await client.flush_contexts()
            mock_bulk.assert_not_called()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_flush_exception_swallowed(self, mock_bulk):
        mock_bulk.side_effect = httpx.ConnectError("fail")

        async def _run():
            client = _make_async_flags_client()
            client.register(Context("user", "u-1"))
            await client.flush_contexts()  # Should not raise

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_contexts_bg(self, mock_bulk):
        """_flush_contexts_bg does a sync POST from background thread."""
        mock_bulk.return_value = _ok_response()
        client = _make_async_flags_client()
        client.register(Context("user", "u-1"))
        client._flush_contexts_bg()
        mock_bulk.assert_called_once()

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_contexts_bg_empty(self, mock_bulk):
        client = _make_async_flags_client()
        client._flush_contexts_bg()
        mock_bulk.assert_not_called()

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_contexts_bg_exception_swallowed(self, mock_bulk):
        mock_bulk.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        client.register(Context("user", "u-1"))
        client._flush_contexts_bg()  # Should not raise


# ---------------------------------------------------------------------------
# Async FlagsClient: Evaluate
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientEvaluate:
    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_evaluate_connected_uses_store(self, mock_list):
        async def _run():
            client = _make_async_flags_client()
            client._connected = True
            client._flag_store = {
                "my-flag": {
                    "key": "my-flag",
                    "default": "off",
                    "environments": {"prod": {"enabled": True, "default": "env-default", "rules": []}},
                }
            }
            result = await client.evaluate("my-flag", environment="prod", context=[Context("user", "u-1")])
            assert result == "env-default"
            mock_list.assert_not_called()

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_evaluate_not_connected_fetches(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = _make_async_flags_client()
            result = await client.evaluate("test-flag", environment="prod", context=[Context("user", "u-1")])
            assert result is False
            mock_list.assert_called_once()

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_evaluate_flag_not_found(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = _make_async_flags_client()
            result = await client.evaluate("nonexistent", environment="prod", context=[Context("user", "u-1")])
            assert result is None

        asyncio.run(_run())


class TestAsyncFlagsClientEvaluateHandle:
    def test_not_connected_raises(self):
        from smplkit._errors import SmplNotConnectedError

        client = _make_async_flags_client()
        with pytest.raises(SmplNotConnectedError, match="not connected"):
            client._evaluate_handle("key", "default_val", None)

    def test_with_explicit_context(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": False,
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True}],
                    },
                },
            }
        }
        result = client._evaluate_handle("flag-a", False, [Context("user", "u-1", plan="enterprise")])
        assert result is True

    def test_with_context_provider(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": "off",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        client._context_provider = lambda: [Context("user", "u-1")]
        result = client._evaluate_handle("flag-a", "off", None)
        assert result == "off"
        assert client._context_buffer.pending_count > 0

    @patch("smplkit.flags.client.threading.Thread")
    def test_context_provider_triggers_flush(self, mock_thread):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {"flag-a": {"key": "flag-a", "default": False, "environments": {}}}
        for i in range(100):
            client._context_buffer.observe([Context("user", f"u-{i}")])
        client._context_provider = lambda: [Context("user", "trigger")]
        client._evaluate_handle("flag-a", False, None)
        mock_thread.assert_called_once()

    def test_no_provider_empty_context(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": "fallback",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        result = client._evaluate_handle("flag-a", "fallback", None)
        assert result == "fallback"

    def test_flag_not_in_store(self):
        client = _make_async_flags_client()
        client._connected = True
        client._flag_store = {}
        result = client._evaluate_handle("missing", "default_val", [Context("user", "u-1")])
        assert result == "default_val"

    def test_evaluate_none_becomes_default(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {"flag-a": {"key": "flag-a", "default": None, "environments": {}}}
        result = client._evaluate_handle("flag-a", "my-default", [Context("user", "u-1")])
        assert result == "my-default"

    def test_cache_hit(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "default": "val",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        ctx = [Context("user", "u-1")]
        client._evaluate_handle("flag-a", "val", ctx)
        client._evaluate_handle("flag-a", "val", ctx)
        assert client._cache.cache_hits == 1


# ---------------------------------------------------------------------------
# Async FlagsClient: Event handlers + listeners
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientEventHandlers:
    """Async WS event handlers use sync list_flags (called from WS thread)."""

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_flag_changed({"key": "test-flag"})
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed_fetch_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        # Should not raise — error is caught and logged
        client._handle_flag_changed({"key": "test-flag"})

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_flag_deleted({"key": "test-flag"})
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted_fetch_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        client._handle_flag_deleted({"key": "test-flag"})


class TestAsyncFlagsClientChangeListeners:
    def test_fire_global_and_handle_listeners(self):
        client = _make_async_flags_client()
        global_listener = MagicMock()
        handle_listener = MagicMock()
        client._global_listeners.append(global_listener)
        handle = client.boolFlag("my-flag", False)
        handle.on_change(handle_listener)
        client._fire_change_listeners("my-flag", "websocket")
        global_listener.assert_called_once()
        handle_listener.assert_called_once()

    def test_global_listener_exception_swallowed(self):
        client = _make_async_flags_client()
        bad = MagicMock(side_effect=RuntimeError("boom"))
        good = MagicMock()
        client._global_listeners.extend([bad, good])
        client._fire_change_listeners("flag-a", "websocket")
        good.assert_called_once()

    def test_handle_listener_exception_swallowed(self):
        client = _make_async_flags_client()
        handle = client.boolFlag("my-flag", False)
        handle.on_change(MagicMock(side_effect=RuntimeError("boom")))
        client._fire_change_listeners("my-flag", "websocket")

    def test_none_key_fires_nothing(self):
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._fire_change_listeners(None, "websocket")
        listener.assert_not_called()

    def test_fire_change_listeners_all(self):
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._flag_store = {"a": {"key": "a"}, "b": {"key": "b"}}
        client._fire_change_listeners_all("manual")
        assert listener.call_count == 2


# ---------------------------------------------------------------------------
# Async FlagsClient: Model conversion + internals
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientInternals:
    def test_to_model(self):
        client = _make_async_flags_client()
        parsed = _mock_flag_response()
        result = client._to_model(parsed)
        assert isinstance(result, AsyncFlag)
        assert result.key == "test-flag"

    def test_resource_to_model(self):
        client = _make_async_flags_client()
        resource = _mock_flag_response().data
        result = client._resource_to_model(resource)
        assert isinstance(result, AsyncFlag)
        assert result.id == _TEST_UUID

    def test_parse_gen_context_type_response(self):
        from smplkit.flags.client import _parse_gen_context_type_response

        parsed = _parsed_ct_response(id="ct-1", key="user", name="User")
        ct = _parse_gen_context_type_response(parsed)
        assert ct.key == "user"

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_all_flags(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = _make_async_flags_client()
            await client._fetch_all_flags()
            assert "test-flag" in client._flag_store

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list(self, mock_list):
        mock_list.return_value = _ok_response(parsed=_mock_list_parsed())

        async def _run():
            client = _make_async_flags_client()
            result = await client._fetch_flags_list()
            assert len(result) == 1
            assert result[0]["key"] == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list_empty(self, mock_list):
        mock_list.return_value = _ok_response(parsed=None)

        async def _run():
            client = _make_async_flags_client()
            result = await client._fetch_flags_list()
            assert result == []

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplConnectionError):
                await client._fetch_flags_list()

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError, match="unexpected"):
                await client._fetch_flags_list()

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Async FlagsClient: Handle factories + misc runtime
# ---------------------------------------------------------------------------


class TestAsyncFlagsClientRuntime:
    def test_bool_flag(self):
        client = _make_async_flags_client()
        handle = client.boolFlag("test", False)
        assert handle.key == "test"

    def test_string_flag(self):
        client = _make_async_flags_client()
        handle = client.stringFlag("color", "red")
        assert handle.key == "color"

    def test_number_flag(self):
        client = _make_async_flags_client()
        handle = client.numberFlag("retries", 3)
        assert handle.key == "retries"

    def test_json_flag(self):
        client = _make_async_flags_client()
        handle = client.jsonFlag("config", {"a": 1})
        assert handle.key == "config"

    def test_context_provider(self):
        client = _make_async_flags_client()

        @client.context_provider
        def provider():
            return [Context("user", "u-1")]

        assert client._context_provider is provider

    def test_on_change(self):
        client = _make_async_flags_client()

        @client.on_change
        def listener(event):
            pass

        assert len(client._global_listeners) == 1

    def test_register_single(self):
        client = _make_async_flags_client()
        client.register(Context("user", "u-1", plan="enterprise"))
        batch = client._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["type"] == "user"
        assert batch[0]["key"] == "u-1"

    def test_register_list(self):
        client = _make_async_flags_client()
        client.register([Context("user", "u-1"), Context("account", "acme-corp")])
        batch = client._context_buffer.drain()
        assert len(batch) == 2
