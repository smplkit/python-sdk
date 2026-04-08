"""Tests for prescriptive config access: resolve, subscribe, LiveConfigProxy, change listeners."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.config.client import ConfigChangeEvent, LiveConfigProxy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connected_client(cache=None):
    """Create a SmplClient with a pre-populated config cache."""
    client = SmplClient(api_key="sk_test", environment="production", service="svc")
    if cache is None:
        cache = {
            "db": {
                "host": "localhost",
                "port": 5432,
                "retries": 3,
                "enabled": True,
                "name": "test",
                "ratio": 0.75,
            },
        }
    client.config._config_cache = cache
    client.config._connected = True
    return client


def _make_connected_async_client(cache=None):
    """Create an AsyncSmplClient with a pre-populated config cache."""
    client = AsyncSmplClient(api_key="sk_test", environment="production", service="svc")
    if cache is None:
        cache = {
            "db": {
                "host": "localhost",
                "port": 5432,
                "retries": 3,
                "enabled": True,
                "name": "test",
                "ratio": 0.75,
            },
        }
    client.config._config_cache = cache
    client.config._connected = True
    return client


# ===================================================================
# 1. resolve() — sync
# ===================================================================


class TestResolveSyncPrescriptive:
    def test_resolve_returns_flat_dict(self):
        client = _make_connected_client()
        result = client.config.resolve("db")
        assert result == {
            "host": "localhost",
            "port": 5432,
            "retries": 3,
            "enabled": True,
            "name": "test",
            "ratio": 0.75,
        }

    def test_resolve_returns_empty_for_missing_config(self):
        client = _make_connected_client()
        assert client.config.resolve("nonexistent") == {}

    def test_resolve_with_dataclass_model(self):
        client = _make_connected_client({"db": {"host": "localhost", "port": 5432}})

        class DbConfig:
            def __init__(self, host, port):
                self.host = host
                self.port = port

        result = client.config.resolve("db", model=DbConfig)
        assert isinstance(result, DbConfig)
        assert result.host == "localhost"
        assert result.port == 5432

    def test_resolve_with_pydantic_model(self):
        client = _make_connected_client({"db": {"host": "localhost", "port": 5432}})

        class FakePydantic:
            @classmethod
            def model_validate(cls, data):
                obj = cls()
                obj.host = data["host"]
                obj.port = data["port"]
                return obj

        result = client.config.resolve("db", model=FakePydantic)
        assert isinstance(result, FakePydantic)
        assert result.host == "localhost"

    def test_resolve_unflattens_dot_keys_for_model(self):
        client = _make_connected_client({"svc": {"database.host": "h", "database.port": 5432, "retries": 3}})

        class SvcConfig:
            def __init__(self, database, retries):
                self.database = database
                self.retries = retries

        result = client.config.resolve("svc", model=SvcConfig)
        assert result.database == {"host": "h", "port": 5432}
        assert result.retries == 3

    def test_resolve_triggers_lazy_connect(self):
        client = SmplClient(api_key="sk_test", environment="production", service="svc")
        with patch.object(client.config, "_connect_internal") as mock_connect:
            client.config._config_cache = {"db": {"host": "h"}}
            client.config.resolve("db")
        mock_connect.assert_called_once()


# ===================================================================
# 2. resolve() — async
# ===================================================================


class TestResolveAsyncPrescriptive:
    def test_resolve_returns_flat_dict(self):
        client = _make_connected_async_client()

        async def _run():
            result = await client.config.resolve("db")
            assert result["host"] == "localhost"
            assert result["port"] == 5432

        asyncio.run(_run())

    def test_resolve_returns_empty_for_missing_config(self):
        client = _make_connected_async_client()

        async def _run():
            assert await client.config.resolve("nonexistent") == {}

        asyncio.run(_run())

    def test_resolve_with_dataclass_model(self):
        client = _make_connected_async_client({"db": {"host": "localhost", "port": 5432}})

        class DbConfig:
            def __init__(self, host, port):
                self.host = host
                self.port = port

        async def _run():
            result = await client.config.resolve("db", model=DbConfig)
            assert isinstance(result, DbConfig)
            assert result.host == "localhost"

        asyncio.run(_run())

    def test_resolve_with_pydantic_model(self):
        client = _make_connected_async_client({"db": {"host": "localhost", "port": 5432}})

        class FakePydantic:
            @classmethod
            def model_validate(cls, data):
                obj = cls()
                obj.host = data["host"]
                return obj

        async def _run():
            result = await client.config.resolve("db", model=FakePydantic)
            assert isinstance(result, FakePydantic)

        asyncio.run(_run())


# ===================================================================
# 3. subscribe() + LiveConfigProxy — sync
# ===================================================================


class TestSubscribeSyncPrescriptive:
    def test_subscribe_returns_proxy(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        assert isinstance(proxy, LiveConfigProxy)

    def test_proxy_attribute_access(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        assert proxy.host == "localhost"
        assert proxy.port == 5432

    def test_proxy_getitem_access(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        assert proxy["host"] == "localhost"
        assert proxy["port"] == 5432

    def test_proxy_reflects_cache_updates(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        assert proxy.host == "localhost"

        # Simulate cache update (as refresh() would do)
        client.config._config_cache["db"]["host"] = "new-host"
        assert proxy.host == "new-host"

    def test_proxy_missing_attribute_raises(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        with pytest.raises(AttributeError, match="No config item"):
            _ = proxy.nonexistent

    def test_proxy_missing_getitem_raises(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        with pytest.raises(KeyError):
            _ = proxy["nonexistent"]

    def test_proxy_with_model(self):
        client = _make_connected_client({"db": {"host": "localhost", "port": 5432}})

        class DbConfig:
            def __init__(self, host, port):
                self.host = host
                self.port = port

        proxy = client.config.subscribe("db", model=DbConfig)
        assert proxy.host == "localhost"
        assert proxy.port == 5432

    def test_proxy_with_pydantic_model(self):
        client = _make_connected_client({"db": {"host": "localhost", "port": 5432}})

        class FakePydantic:
            @classmethod
            def model_validate(cls, data):
                obj = cls()
                obj.host = data["host"]
                obj.port = data["port"]
                return obj

        proxy = client.config.subscribe("db", model=FakePydantic)
        assert proxy.host == "localhost"

    def test_proxy_repr_without_model(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("db")
        r = repr(proxy)
        assert "LiveConfigProxy" in r
        assert "db" in r

    def test_proxy_repr_with_model(self):
        client = _make_connected_client({"db": {"host": "localhost"}})

        class DbConfig:
            def __init__(self, host):
                self.host = host

        proxy = client.config.subscribe("db", model=DbConfig)
        r = repr(proxy)
        assert "LiveConfigProxy" in r
        assert "DbConfig" in r

    def test_proxy_for_missing_config_returns_empty(self):
        client = _make_connected_client()
        proxy = client.config.subscribe("nonexistent")
        # getitem on empty cache
        with pytest.raises(KeyError):
            _ = proxy["anything"]


# ===================================================================
# 4. subscribe() + LiveConfigProxy — async
# ===================================================================


class TestSubscribeAsyncPrescriptive:
    def test_subscribe_returns_proxy(self):
        client = _make_connected_async_client()

        async def _run():
            proxy = await client.config.subscribe("db")
            assert isinstance(proxy, LiveConfigProxy)

        asyncio.run(_run())

    def test_proxy_attribute_access(self):
        client = _make_connected_async_client()

        async def _run():
            proxy = await client.config.subscribe("db")
            assert proxy.host == "localhost"

        asyncio.run(_run())

    def test_proxy_getitem_access(self):
        client = _make_connected_async_client()

        async def _run():
            proxy = await client.config.subscribe("db")
            assert proxy["host"] == "localhost"

        asyncio.run(_run())

    def test_proxy_reflects_cache_updates(self):
        client = _make_connected_async_client()

        async def _run():
            proxy = await client.config.subscribe("db")
            assert proxy.host == "localhost"
            client.config._config_cache["db"]["host"] = "updated"
            assert proxy.host == "updated"

        asyncio.run(_run())


# ===================================================================
# 5. Refresh — sync
# ===================================================================


class TestRefreshSync:
    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_refresh_updates_cache(self, mock_list):
        client = _make_connected_client({"db": {"host": "old"}})

        mock_attrs = MagicMock()
        mock_attrs.name = "DB"
        mock_attrs.key = "db"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.items = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = "cfg-1"
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.parsed = mock_parsed
        mock_list.return_value = mock_response

        with patch(
            "smplkit.config.models.Config._build_chain",
            return_value=[{"id": "cfg-1", "items": {}, "values": {"host": "new-host"}, "environments": {}}],
        ):
            client.config.refresh()

        assert client.config._config_cache["db"]["host"] == "new-host"

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_refresh_fires_listeners(self, mock_list):
        client = _make_connected_client({"db": {"host": "old"}})

        events = []
        client.config.on_change(lambda e: events.append(e))

        mock_attrs = MagicMock()
        mock_attrs.name = "DB"
        mock_attrs.key = "db"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.items = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = "cfg-1"
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.parsed = mock_parsed
        mock_list.return_value = mock_response

        with patch(
            "smplkit.config.models.Config._build_chain",
            return_value=[{"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}],
        ):
            client.config.refresh()

        assert len(events) == 1
        assert events[0].config_key == "db"
        assert events[0].item_key == "host"
        assert events[0].old_value == "old"
        assert events[0].new_value == "new-host"
        assert events[0].source == "manual"


# ===================================================================
# 6. Refresh — async
# ===================================================================


class TestRefreshAsync:
    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_refresh_updates_cache(self, mock_list):
        client = _make_connected_async_client({"db": {"host": "old"}})

        mock_attrs = MagicMock()
        mock_attrs.name = "DB"
        mock_attrs.key = "db"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.items = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = "cfg-1"
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        async def fake_list(*args, **kwargs):
            return mock_response

        mock_list.side_effect = fake_list

        async def run():
            with patch(
                "smplkit.config.models.AsyncConfig._build_chain",
                return_value=[{"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}],
            ):
                await client.config.refresh()

        asyncio.run(run())
        assert client.config._config_cache["db"]["host"] == "new-host"

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_refresh_fires_listeners(self, mock_list):
        client = _make_connected_async_client({"db": {"host": "old"}})

        events = []
        client.config.on_change(lambda e: events.append(e))

        mock_attrs = MagicMock()
        mock_attrs.name = "DB"
        mock_attrs.key = "db"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.items = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = "cfg-1"
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        async def fake_list(*args, **kwargs):
            return mock_response

        mock_list.side_effect = fake_list

        async def run():
            with patch(
                "smplkit.config.models.AsyncConfig._build_chain",
                return_value=[{"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}],
            ):
                await client.config.refresh()

        asyncio.run(run())
        assert len(events) == 1
        assert events[0].source == "manual"


# ===================================================================
# 7. ConfigChangeEvent
# ===================================================================


class TestConfigChangeEvent:
    def test_attributes(self):
        event = ConfigChangeEvent(
            config_key="db",
            item_key="host",
            old_value="old",
            new_value="new",
            source="manual",
        )
        assert event.config_key == "db"
        assert event.item_key == "host"
        assert event.old_value == "old"
        assert event.new_value == "new"
        assert event.source == "manual"

    def test_repr(self):
        event = ConfigChangeEvent(
            config_key="db",
            item_key="host",
            old_value="old",
            new_value="new",
            source="websocket",
        )
        r = repr(event)
        assert "ConfigChangeEvent" in r
        assert "db" in r
        assert "host" in r


# ===================================================================
# 8. LiveConfigProxy — direct unit tests
# ===================================================================


class TestLiveConfigProxyDirect:
    def test_current_values_reads_from_cache(self):
        client = _make_connected_client({"db": {"host": "h", "port": 5432}})
        proxy = LiveConfigProxy(client.config, "db")
        assert proxy._current_values() == {"host": "h", "port": 5432}

    def test_current_values_missing_key(self):
        client = _make_connected_client({})
        proxy = LiveConfigProxy(client.config, "missing")
        assert proxy._current_values() == {}

    def test_build_model_without_model(self):
        client = _make_connected_client({"db": {"host": "h"}})
        proxy = LiveConfigProxy(client.config, "db")
        result = proxy._build_model()
        assert result == {"host": "h"}

    def test_build_model_with_model(self):
        client = _make_connected_client({"db": {"host": "h", "port": 5432}})

        class DbConfig:
            def __init__(self, host, port):
                self.host = host
                self.port = port

        proxy = LiveConfigProxy(client.config, "db", model=DbConfig)
        result = proxy._build_model()
        assert isinstance(result, DbConfig)
        assert result.host == "h"

    def test_build_model_with_pydantic(self):
        client = _make_connected_client({"db": {"host": "h"}})

        class FakePydantic:
            @classmethod
            def model_validate(cls, data):
                obj = cls()
                obj.host = data["host"]
                return obj

        proxy = LiveConfigProxy(client.config, "db", model=FakePydantic)
        result = proxy._build_model()
        assert result.host == "h"

    def test_build_model_unflattens_dot_keys(self):
        client = _make_connected_client({"db": {"database.host": "h", "database.port": 5432}})

        class DbConfig:
            def __init__(self, database):
                self.database = database

        proxy = LiveConfigProxy(client.config, "db", model=DbConfig)
        result = proxy._build_model()
        assert result.database == {"host": "h", "port": 5432}
