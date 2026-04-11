"""Tests for ConfigClient and AsyncConfigClient."""

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
from smplkit.config.client import AsyncConfigClient, LiveConfigProxy

_TEST_UUID = "5a0c6be1-0000-0000-0000-000000000001"
_TEST_UUID_2 = "5a0c6be1-0000-0000-0000-000000000002"


def _mock_attrs(*, name="Test", description=None, parent=None, items=None, environments=None):
    """Create a mock attributes object for a config resource."""
    attrs = MagicMock()
    attrs.name = name
    attrs.description = description
    attrs.parent = parent
    attrs.items = items
    attrs.environments = environments
    attrs.created_at = None
    attrs.updated_at = None
    return attrs


def _mock_response(*, status_code=HTTPStatus.OK, parsed=None, content=b""):
    """Create a mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.parsed = parsed
    return resp


def _mock_list_response(resources):
    """Create a mock list response with the given resources."""
    parsed = MagicMock()
    parsed.data = resources
    return _mock_response(parsed=parsed)


def _mock_single_response(resource, status_code=HTTPStatus.OK):
    """Create a mock single-resource response."""
    parsed = MagicMock()
    parsed.data = resource
    return _mock_response(status_code=status_code, parsed=parsed)


def _mock_resource(id="test", **attr_kwargs):
    """Create a mock resource with attributes."""
    resource = MagicMock()
    resource.id = id
    resource.attributes = _mock_attrs(**attr_kwargs)
    return resource


# ===================================================================
# ConfigClient — new()
# ===================================================================


class TestConfigClientNew:
    def test_new_returns_config_with_no_created_at(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("my_service")
        assert cfg.id == "my_service"
        assert cfg.created_at is None
        assert cfg.name == "My Service"  # auto-generated from id

    def test_new_with_explicit_name(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("my_service", name="Custom Name")
        assert cfg.name == "Custom Name"

    def test_new_with_description_and_parent(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("child_svc", description="A child", parent=_TEST_UUID)
        assert cfg.description == "A child"
        assert cfg.parent == _TEST_UUID


# ===================================================================
# ConfigClient — get() by id
# ===================================================================


class TestConfigClientGet:
    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_by_id(self, mock_get):
        resource = _mock_resource(id="common", name="Common")
        mock_get.return_value = _mock_single_response(resource)

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.get("common")
        assert cfg.id == "common"
        mock_get.assert_called_once()

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_not_found_404(self, mock_get):
        mock_get.return_value = _mock_response(status_code=HTTPStatus.NOT_FOUND, content=b"Not Found")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplNotFoundError):
            client.config.get("nonexistent")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_not_found_parsed_none(self, mock_get):
        mock_get.return_value = _mock_response(parsed=None)
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplNotFoundError):
            client.config.get("missing")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_not_found_no_data_attr(self, mock_get):
        parsed = MagicMock(spec=[])  # no .data attribute
        mock_get.return_value = _mock_response(parsed=parsed)
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplNotFoundError):
            client.config.get("missing")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_network_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("connection refused")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplConnectionError):
            client.config.get("common")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_timeout(self, mock_get):
        mock_get.side_effect = httpx.ReadTimeout("timed out")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplTimeoutError):
            client.config.get("common")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_reraises_non_network_error(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.get("common")


# ===================================================================
# ConfigClient — list()
# ===================================================================


class TestConfigClientList:
    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list(self, mock_list):
        resource = _mock_resource(id="c1", name="Config 1")
        mock_list.return_value = _mock_list_response([resource])

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        configs = client.config.list()
        assert len(configs) == 1
        assert configs[0].id == "c1"

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplConnectionError):
            client.config.list()

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_parsed_none(self, mock_list):
        mock_list.return_value = _mock_response(parsed=None)
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        assert client.config.list() == []

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_no_data_attr(self, mock_list):
        parsed = MagicMock(spec=[])
        mock_list.return_value = _mock_response(parsed=parsed)
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        assert client.config.list() == []

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_reraises_non_network_error(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.list()


# ===================================================================
# ConfigClient — delete() by id
# ===================================================================


class TestConfigClientDelete:
    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete_by_id(self, mock_delete):
        mock_delete.return_value = _mock_response(status_code=HTTPStatus.NO_CONTENT)

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config.delete("my_config")

        mock_delete.assert_called_once()

    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.ConnectError("refused")

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(SmplConnectionError):
            client.config.delete("my_config")

    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete_reraises_non_network_error(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.delete("my_config")


# ===================================================================
# ConfigClient — _create_config / _update_config_from_model (for Config.save)
# ===================================================================


class TestConfigClientCreateUpdate:
    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_config(self, mock_create):
        resource = _mock_resource(id="new_config", name="New Config")
        mock_create.return_value = _mock_single_response(resource, status_code=HTTPStatus.CREATED)

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("new_config")
        result = client.config._create_config(cfg)
        assert result.id == "new_config"
        assert result.name == "New Config"

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_config_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("test")
        with pytest.raises(SmplConnectionError):
            client.config._create_config(cfg)

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_config_parsed_none(self, mock_create):
        mock_create.return_value = _mock_response(parsed=None)
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("test")
        with pytest.raises(SmplValidationError):
            client.config._create_config(cfg)

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_config_reraises_non_network_error(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("test")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config._create_config(cfg)

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_from_model(self, mock_update):
        resource = _mock_resource(id="test", name="Updated")
        mock_update.return_value = _mock_single_response(resource)

        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        from smplkit.config.models import Config

        cfg = Config(client.config, id="test", name="Old")
        result = client.config._update_config_from_model(cfg)
        assert result.name == "Updated"

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_from_model_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        from smplkit.config.models import Config

        cfg = Config(client.config, id="test", name="T")
        with pytest.raises(SmplConnectionError):
            client.config._update_config_from_model(cfg)

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_from_model_parsed_none(self, mock_update):
        mock_update.return_value = _mock_response(parsed=None)
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        from smplkit.config.models import Config

        cfg = Config(client.config, id="test", name="T")
        with pytest.raises(SmplValidationError):
            client.config._update_config_from_model(cfg)

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_from_model_reraises_non_network_error(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        from smplkit.config.models import Config

        cfg = Config(client.config, id="test", name="T")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config._update_config_from_model(cfg)


# ===================================================================
# ConfigClient — _connect_internal
# ===================================================================


class TestConfigClientConnectInternal:
    def _make_mock_config(self, id, items_raw, environments=None):
        cfg = MagicMock()
        cfg.id = id
        cfg._items_raw = items_raw
        cfg.environments = environments or {}
        cfg._build_chain.return_value = [{"id": id, "items": items_raw, "environments": environments or {}}]
        return cfg

    def test_connect_internal_populates_cache(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        mock_cfg = self._make_mock_config("db", {"host": {"value": "localhost"}})
        with patch.object(client.config, "list", return_value=[mock_cfg]):
            client.config._connect_internal()
        assert client.config._connected is True
        assert "db" in client.config._config_cache

    def test_connect_internal_is_idempotent(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        mock_cfg = self._make_mock_config("db", {"host": {"value": "localhost"}})
        with patch.object(client.config, "list", return_value=[mock_cfg]) as mock_list:
            client.config._connect_internal()
            client.config._connect_internal()
        mock_list.assert_called_once()


# ===================================================================
# ConfigClient — resolve()
# ===================================================================


class TestConfigClientResolve:
    def test_resolve_returns_flat_dict(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"db": {"host": "localhost", "port": 5432}}

        result = client.config.resolve("db")
        assert result == {"host": "localhost", "port": 5432}

    def test_resolve_returns_empty_for_missing_id(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {}

        assert client.config.resolve("missing") == {}

    def test_resolve_triggers_connect(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with patch.object(client.config, "_connect_internal") as mock_connect:
            with patch.object(client.config, "_config_cache", {"db": {"host": "h"}}):
                client.config.resolve("db")
        mock_connect.assert_called_once()

    def test_resolve_with_model_class(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"db": {"host": "localhost", "port": 5432}}

        class DbConfig:
            def __init__(self, host, port):
                self.host = host
                self.port = port

        result = client.config.resolve("db", model=DbConfig)
        assert isinstance(result, DbConfig)
        assert result.host == "localhost"
        assert result.port == 5432

    def test_resolve_with_pydantic_model(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"db": {"host": "localhost", "port": 5432}}

        class FakePydanticModel:
            @classmethod
            def model_validate(cls, data):
                obj = cls()
                obj.host = data["host"]
                obj.port = data["port"]
                return obj

        result = client.config.resolve("db", model=FakePydanticModel)
        assert isinstance(result, FakePydanticModel)
        assert result.host == "localhost"

    def test_resolve_unflattens_dot_notation(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"svc": {"database.host": "h", "database.port": 5432}}

        class SvcConfig:
            def __init__(self, database):
                self.database = database

        result = client.config.resolve("svc", model=SvcConfig)
        assert result.database == {"host": "h", "port": 5432}


# ===================================================================
# ConfigClient — subscribe()
# ===================================================================


class TestConfigClientSubscribe:
    def test_subscribe_returns_live_proxy(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"db": {"host": "localhost"}}

        proxy = client.config.subscribe("db")
        assert isinstance(proxy, LiveConfigProxy)

    def test_subscribe_triggers_connect(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        with patch.object(client.config, "_connect_internal") as mock_connect:
            with patch.object(client.config, "_config_cache", {"db": {"host": "h"}}):
                client.config.subscribe("db")
        mock_connect.assert_called_once()


# ===================================================================
# ConfigClient — refresh()
# ===================================================================


class TestConfigClientRefresh:
    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_refresh_updates_cache(self, mock_list):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"db": {"host": "old"}}

        resource = _mock_resource(id="db", name="DB")
        mock_list.return_value = _mock_list_response([resource])

        with patch(
            "smplkit.config.models.Config._build_chain",
            return_value=[{"id": "cfg-1", "items": {}, "values": {"host": "new-host"}, "environments": {}}],
        ):
            client.config.refresh()

        assert client.config._config_cache["db"]["host"] == "new-host"

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_refresh_fires_listeners(self, mock_list):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        client.config._connected = True
        client.config._config_cache = {"db": {"host": "old"}}

        events = []
        client.config.on_change(lambda e: events.append(e))

        resource = _mock_resource(id="db", name="DB")
        mock_list.return_value = _mock_list_response([resource])

        with patch(
            "smplkit.config.models.Config._build_chain",
            return_value=[{"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}],
        ):
            client.config.refresh()

        assert len(events) == 1
        assert events[0].config_id == "db"
        assert events[0].item_key == "host"
        assert events[0].old_value == "old"
        assert events[0].new_value == "new-host"
        assert events[0].source == "manual"


# ===================================================================
# ConfigClient — on_change() dual-mode decorator
# ===================================================================


class TestConfigClientOnChange:
    def test_bare_decorator(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change
        def handler(event):
            pass

        assert len(client.config._listeners) == 1
        fn, ci, ik = client.config._listeners[0]
        assert fn is handler
        assert ci is None
        assert ik is None

    def test_with_config_id(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change("db")
        def handler(event):
            pass

        assert len(client.config._listeners) == 1
        fn, ci, ik = client.config._listeners[0]
        assert fn is handler
        assert ci == "db"
        assert ik is None

    def test_with_config_id_and_item_key(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change("db", item_key="host")
        def handler(event):
            pass

        assert len(client.config._listeners) == 1
        fn, ci, ik = client.config._listeners[0]
        assert fn is handler
        assert ci == "db"
        assert ik == "host"

    def test_empty_parens_decorator(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change()
        def handler(event):
            pass

        assert len(client.config._listeners) == 1
        fn, ci, ik = client.config._listeners[0]
        assert fn is handler
        assert ci is None
        assert ik is None

    def test_returns_original_function(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")

        def handler(event):
            pass

        result = client.config.on_change(handler)
        assert result is handler

    def test_config_id_decorator_returns_original_function(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change("db")
        def handler(event):
            pass

        # The outer call returns a decorator that returns the original fn
        assert callable(handler)


# ===================================================================
# ConfigClient — _fire_change_listeners
# ===================================================================


class TestFireChangeListeners:
    def test_filters_by_config_id(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        events = []

        @client.config.on_change("db")
        def handler(event):
            events.append(event)

        client.config._fire_change_listeners(
            {"db": {"host": "old"}, "other": {"x": 1}},
            {"db": {"host": "new"}, "other": {"x": 2}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].config_id == "db"

    def test_filters_by_item_key(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        events = []

        @client.config.on_change("db", item_key="host")
        def handler(event):
            events.append(event)

        client.config._fire_change_listeners(
            {"db": {"host": "old", "port": 1}},
            {"db": {"host": "new", "port": 2}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].item_key == "host"

    def test_no_change_fires_nothing(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "same"}},
            {"db": {"host": "same"}},
            source="manual",
        )
        assert len(events) == 0

    def test_listener_exception_is_caught(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        good_events = []

        def bad_listener(event):
            raise ValueError("boom")

        client.config.on_change(bad_listener)
        client.config.on_change(lambda e: good_events.append(e))

        client.config._fire_change_listeners(
            {"db": {"host": "old"}},
            {"db": {"host": "new"}},
            source="manual",
        )
        assert len(good_events) == 1

    def test_new_config_in_new_cache(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {},
            {"db": {"host": "new"}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].old_value is None
        assert events[0].new_value == "new"

    def test_removed_config_in_new_cache(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "old"}},
            {},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].old_value == "old"
        assert events[0].new_value is None


# ===================================================================
# ConfigClient — _to_model / _resource_to_model
# ===================================================================


class TestConfigClientModelConversion:
    def test_to_model(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        resource = _mock_resource(id="test", name="Test")
        parsed = MagicMock()
        parsed.data = resource
        cfg = client.config._to_model(parsed)
        assert cfg.id == "test"

    def test_resource_to_model(self):
        client = SmplClient(api_key="sk_test", environment="test", service="svc")
        resource = _mock_resource(id="test", name="Test", description="desc")
        cfg = client.config._resource_to_model(resource)
        assert cfg.id == "test"
        assert cfg.name == "Test"


# ===================================================================
# AsyncConfigClient — new()
# ===================================================================


class TestAsyncConfigClientNew:
    def test_new_returns_async_config_with_no_created_at(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("my_service")
        assert cfg.id == "my_service"
        assert cfg.created_at is None
        assert cfg.name == "My Service"

    def test_new_with_explicit_name(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("my_service", name="Custom Name")
        assert cfg.name == "Custom Name"

    def test_new_with_description_and_parent(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        cfg = client.config.new("child_svc", description="A child", parent=_TEST_UUID)
        assert cfg.description == "A child"
        assert cfg.parent == _TEST_UUID


# ===================================================================
# AsyncConfigClient — get() by id
# ===================================================================


class TestAsyncConfigClientGet:
    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_by_id(self, mock_get):
        resource = _mock_resource(id="common", name="Common")
        mock_get.return_value = _mock_single_response(resource)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            cfg = await client.config.get("common")
            assert cfg.id == "common"

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_not_found_404(self, mock_get):
        mock_get.return_value = _mock_response(status_code=HTTPStatus.NOT_FOUND, content=b"Not Found")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplNotFoundError):
                await client.config.get("nonexistent")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_not_found_parsed_none(self, mock_get):
        mock_get.return_value = _mock_response(parsed=None)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplNotFoundError):
                await client.config.get("missing")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_not_found_no_data_attr(self, mock_get):
        parsed = MagicMock(spec=[])
        mock_get.return_value = _mock_response(parsed=parsed)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplNotFoundError):
                await client.config.get("missing")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_network_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplConnectionError):
                await client.config.get("common")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_timeout(self, mock_get):
        mock_get.side_effect = httpx.ReadTimeout("timed out")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplTimeoutError):
                await client.config.get("common")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_reraises_non_network_error(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.get("common")

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — list()
# ===================================================================


class TestAsyncConfigClientList:
    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list(self, mock_list):
        resource = _mock_resource(id="c1", name="C1")
        mock_list.return_value = _mock_list_response([resource])

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            configs = await client.config.list()
            assert len(configs) == 1

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplConnectionError):
                await client.config.list()

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_parsed_none(self, mock_list):
        mock_list.return_value = _mock_response(parsed=None)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            result = await client.config.list()
            assert result == []

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_no_data_attr(self, mock_list):
        parsed = MagicMock(spec=[])
        mock_list.return_value = _mock_response(parsed=parsed)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            result = await client.config.list()
            assert result == []

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_reraises_non_network_error(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.list()

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — delete() by id
# ===================================================================


class TestAsyncConfigClientDelete:
    @patch("smplkit.config.client.delete_config.asyncio_detailed")
    def test_delete_by_id(self, mock_delete):
        mock_delete.return_value = _mock_response(status_code=HTTPStatus.NO_CONTENT)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            await client.config.delete("my_config")

        asyncio.run(_run())
        mock_delete.assert_called_once()

    @patch("smplkit.config.client.delete_config.asyncio_detailed")
    def test_delete_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(SmplConnectionError):
                await client.config.delete("my_config")

        asyncio.run(_run())

    @patch("smplkit.config.client.delete_config.asyncio_detailed")
    def test_delete_reraises_non_network_error(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.delete("my_config")

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — _create_config / _update_config_from_model
# ===================================================================


class TestAsyncConfigClientCreateUpdate:
    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_config(self, mock_create):
        resource = _mock_resource(id="new_config", name="New Config")
        mock_create.return_value = _mock_single_response(resource, status_code=HTTPStatus.CREATED)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            cfg = client.config.new("new_config")
            result = await client.config._create_config(cfg)
            assert result.id == "new_config"

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_config_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            cfg = client.config.new("test")
            with pytest.raises(SmplConnectionError):
                await client.config._create_config(cfg)

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_config_parsed_none(self, mock_create):
        mock_create.return_value = _mock_response(parsed=None)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            cfg = client.config.new("test")
            with pytest.raises(SmplValidationError):
                await client.config._create_config(cfg)

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_config_reraises_non_network_error(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            cfg = client.config.new("test")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config._create_config(cfg)

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_from_model(self, mock_update):
        resource = _mock_resource(id="test", name="Updated")
        mock_update.return_value = _mock_single_response(resource)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            from smplkit.config.models import AsyncConfig

            cfg = AsyncConfig(client.config, id="test", name="Old")
            result = await client.config._update_config_from_model(cfg)
            assert result.name == "Updated"

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_from_model_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            from smplkit.config.models import AsyncConfig

            cfg = AsyncConfig(client.config, id="test", name="T")
            with pytest.raises(SmplConnectionError):
                await client.config._update_config_from_model(cfg)

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_from_model_parsed_none(self, mock_update):
        mock_update.return_value = _mock_response(parsed=None)

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            from smplkit.config.models import AsyncConfig

            cfg = AsyncConfig(client.config, id="test", name="T")
            with pytest.raises(SmplValidationError):
                await client.config._update_config_from_model(cfg)

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_from_model_reraises_non_network_error(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            from smplkit.config.models import AsyncConfig

            cfg = AsyncConfig(client.config, id="test", name="T")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config._update_config_from_model(cfg)

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — _connect_internal
# ===================================================================


class TestAsyncConfigClientConnectInternal:
    def _make_mock_config(self, id, items_raw, environments=None):
        cfg = MagicMock()
        cfg.id = id
        cfg._items_raw = items_raw
        cfg.environments = environments or {}
        cfg._build_chain = AsyncMock(return_value=[{"id": id, "items": items_raw, "environments": environments or {}}])
        return cfg

    def test_connect_internal_populates_cache(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            mock_cfg = self._make_mock_config("db", {"host": {"value": "localhost"}})
            with patch.object(client.config, "list", new_callable=AsyncMock, return_value=[mock_cfg]):
                await client.config._connect_internal()
            assert client.config._connected is True
            assert "db" in client.config._config_cache

        asyncio.run(_run())

    def test_connect_internal_is_idempotent(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            mock_cfg = self._make_mock_config("db", {"host": {"value": "localhost"}})
            with patch.object(client.config, "list", new_callable=AsyncMock, return_value=[mock_cfg]) as mock_list:
                await client.config._connect_internal()
                await client.config._connect_internal()
            mock_list.assert_called_once()

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — resolve()
# ===================================================================


class TestAsyncConfigClientResolve:
    def test_resolve_returns_flat_dict(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {"db": {"host": "localhost", "port": 5432}}
            result = await client.config.resolve("db")
            assert result == {"host": "localhost", "port": 5432}

        asyncio.run(_run())

    def test_resolve_returns_empty_for_missing_id(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {}
            assert await client.config.resolve("missing") == {}

        asyncio.run(_run())

    def test_resolve_with_model_class(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {"db": {"host": "localhost", "port": 5432}}

            class DbConfig:
                def __init__(self, host, port):
                    self.host = host
                    self.port = port

            result = await client.config.resolve("db", model=DbConfig)
            assert isinstance(result, DbConfig)
            assert result.host == "localhost"

        asyncio.run(_run())

    def test_resolve_with_pydantic_model(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {"db": {"host": "localhost", "port": 5432}}

            class FakePydanticModel:
                @classmethod
                def model_validate(cls, data):
                    obj = cls()
                    obj.host = data["host"]
                    return obj

            result = await client.config.resolve("db", model=FakePydanticModel)
            assert isinstance(result, FakePydanticModel)
            assert result.host == "localhost"

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — subscribe()
# ===================================================================


class TestAsyncConfigClientSubscribe:
    def test_subscribe_returns_live_proxy(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {"db": {"host": "localhost"}}
            proxy = await client.config.subscribe("db")
            assert isinstance(proxy, LiveConfigProxy)

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — refresh()
# ===================================================================


class TestAsyncConfigClientRefresh:
    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_refresh_updates_cache(self, mock_list):
        resource = _mock_resource(id="db", name="DB")

        async def fake_list(*args, **kwargs):
            return _mock_list_response([resource])

        mock_list.side_effect = fake_list

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {"db": {"host": "old"}}
            with patch(
                "smplkit.config.models.AsyncConfig._build_chain",
                return_value=[{"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}],
            ):
                await client.config.refresh()
            assert client.config._config_cache["db"]["host"] == "new-host"

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_refresh_fires_listeners(self, mock_list):
        resource = _mock_resource(id="db", name="DB")

        async def fake_list(*args, **kwargs):
            return _mock_list_response([resource])

        mock_list.side_effect = fake_list

        async def _run():
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            client.config._connected = True
            client.config._config_cache = {"db": {"host": "old"}}
            events = []
            client.config.on_change(lambda e: events.append(e))

            with patch(
                "smplkit.config.models.AsyncConfig._build_chain",
                return_value=[{"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}],
            ):
                await client.config.refresh()
            assert len(events) == 1
            assert events[0].source == "manual"

        asyncio.run(_run())


# ===================================================================
# AsyncConfigClient — on_change() dual-mode decorator
# ===================================================================


class TestAsyncConfigClientOnChange:
    def test_bare_decorator(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change
        def handler(event):
            pass

        assert len(client.config._listeners) == 1
        fn, ci, ik = client.config._listeners[0]
        assert fn is handler
        assert ci is None

    def test_with_config_id(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change("db")
        def handler(event):
            pass

        fn, ci, ik = client.config._listeners[0]
        assert ci == "db"

    def test_with_config_id_and_item_key(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change("db", item_key="host")
        def handler(event):
            pass

        fn, ci, ik = client.config._listeners[0]
        assert ci == "db"
        assert ik == "host"

    def test_empty_parens_decorator(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")

        @client.config.on_change()
        def handler(event):
            pass

        fn, ci, ik = client.config._listeners[0]
        assert ci is None

    def test_fire_change_listeners(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "old"}},
            {"db": {"host": "new"}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].config_id == "db"
        assert events[0].item_key == "host"

    def test_fire_change_listeners_filters_work(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        events = []

        @client.config.on_change("db", item_key="host")
        def handler(event):
            events.append(event)

        client.config._fire_change_listeners(
            {"db": {"host": "old", "port": 1}, "other": {"x": 1}},
            {"db": {"host": "new", "port": 2}, "other": {"x": 2}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].item_key == "host"

    def test_no_change_fires_nothing(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "same"}},
            {"db": {"host": "same"}},
            source="manual",
        )
        assert len(events) == 0

    def test_listener_exception_is_caught(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        good_events = []

        def bad_listener(event):
            raise ValueError("boom")

        client.config.on_change(bad_listener)
        client.config.on_change(lambda e: good_events.append(e))

        client.config._fire_change_listeners(
            {"db": {"host": "old"}},
            {"db": {"host": "new"}},
            source="manual",
        )
        assert len(good_events) == 1


# ===================================================================
# AsyncConfigClient — _to_model / _resource_to_model
# ===================================================================


class TestAsyncConfigClientModelConversion:
    def test_init(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        assert isinstance(client.config, AsyncConfigClient)

    def test_to_model(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        resource = _mock_resource(id="test", name="Test")
        parsed = MagicMock()
        parsed.data = resource
        cfg = client.config._to_model(parsed)
        assert cfg.id == "test"

    def test_resource_to_model(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
        resource = _mock_resource(id="test", name="Test")
        cfg = client.config._resource_to_model(resource)
        assert cfg.id == "test"
