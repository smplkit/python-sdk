"""Tests for prescriptive config access: typed accessors, refresh, change listeners."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import SmplNotConnectedError
from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.config.client import ConfigChangeEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_connected_client(cache: dict | None = None):
    """Create a SmplClient with a pre-populated config cache."""
    client = SmplClient(api_key="sk_test", environment="production")
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


def _make_connected_async_client(cache: dict | None = None):
    """Create an AsyncSmplClient with a pre-populated config cache."""
    client = AsyncSmplClient(api_key="sk_test", environment="production")
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
# 1. Typed accessors — sync
# ===================================================================


class TestTypedAccessorsSync:
    def test_get_str_returns_string(self):
        client = _make_connected_client()
        assert client.config.get_str("db", "name") == "test"

    def test_get_str_returns_default_for_non_string(self):
        client = _make_connected_client()
        assert client.config.get_str("db", "port", default="nope") == "nope"

    def test_get_str_returns_default_for_missing(self):
        client = _make_connected_client()
        assert client.config.get_str("db", "ghost") is None

    def test_get_int_returns_int(self):
        client = _make_connected_client()
        assert client.config.get_int("db", "port") == 5432

    def test_get_int_returns_default_for_non_int(self):
        client = _make_connected_client()
        assert client.config.get_int("db", "name", default=0) == 0

    def test_get_int_returns_default_for_bool(self):
        client = _make_connected_client()
        assert client.config.get_int("db", "enabled", default=-1) == -1

    def test_get_bool_returns_bool(self):
        client = _make_connected_client()
        assert client.config.get_bool("db", "enabled") is True

    def test_get_bool_returns_default_for_non_bool(self):
        client = _make_connected_client()
        assert client.config.get_bool("db", "port", default=False) is False

    def test_get_float_returns_float(self):
        client = _make_connected_client()
        assert client.config.get_float("db", "ratio") == 0.75

    def test_get_float_promotes_int(self):
        client = _make_connected_client()
        assert client.config.get_float("db", "port") == 5432.0

    def test_get_float_returns_default_for_bool(self):
        client = _make_connected_client()
        assert client.config.get_float("db", "enabled", default=0.0) == 0.0

    def test_get_float_returns_default_for_string(self):
        client = _make_connected_client()
        assert client.config.get_float("db", "name", default=1.0) == 1.0

    def test_typed_accessors_require_connect(self):
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotConnectedError):
            client.config.get_str("db", "host")
        with pytest.raises(SmplNotConnectedError):
            client.config.get_int("db", "port")
        with pytest.raises(SmplNotConnectedError):
            client.config.get_bool("db", "enabled")


# ===================================================================
# 2. Typed accessors — async
# ===================================================================


class TestTypedAccessorsAsync:
    def test_get_str_returns_string(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_str("db", "name")) == "test"

    def test_get_str_returns_default_for_non_string(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_str("db", "port", default="nope")) == "nope"

    def test_get_int_returns_int(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_int("db", "port")) == 5432

    def test_get_int_returns_default_for_bool(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_int("db", "enabled", default=-1)) == -1

    def test_get_bool_returns_bool(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_bool("db", "enabled")) is True

    def test_get_bool_returns_default_for_non_bool(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_bool("db", "port", default=False)) is False

    def test_get_float_returns_float(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_float("db", "ratio")) == 0.75

    def test_get_float_promotes_int(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_float("db", "port")) == 5432.0

    def test_get_float_returns_default_for_bool(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_float("db", "enabled", default=0.0)) == 0.0

    def test_get_float_returns_default_for_string(self):
        client = _make_connected_async_client()
        assert asyncio.run(client.config.get_float("db", "name", default=1.0)) == 1.0


# ===================================================================
# 3. Refresh — sync
# ===================================================================


class TestRefreshSync:
    def test_refresh_requires_connect(self):
        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotConnectedError):
            client.config.refresh()

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_refresh_updates_cache(self, mock_list):
        client = _make_connected_client({"db": {"host": "old"}})

        # Mock the list response to return a config with new values
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

        # The Config._build_chain is called during refresh
        with patch("smplkit.config.models.Config._build_chain", return_value=[
            {"id": "cfg-1", "items": {}, "values": {"host": "new-host"}, "environments": {}}
        ]):
            client.config.refresh()

        assert client.config.get("db", "host") == "new-host"

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

        with patch("smplkit.config.models.Config._build_chain", return_value=[
            {"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}
        ]):
            client.config.refresh()

        assert len(events) == 1
        assert events[0].config_key == "db"
        assert events[0].item_key == "host"
        assert events[0].old_value == "old"
        assert events[0].new_value == "new-host"
        assert events[0].source == "manual"


# ===================================================================
# 4. Change listeners
# ===================================================================


class TestChangeListeners:
    def test_on_change_registers_listener(self):
        client = _make_connected_client()
        client.config.on_change(lambda e: None)
        assert len(client.config._listeners) == 1

    def test_on_change_with_config_key_filter(self):
        client = _make_connected_client()
        client.config.on_change(lambda e: None, config_key="db")
        assert client.config._listeners[0][1] == "db"

    def test_on_change_with_item_key_filter(self):
        client = _make_connected_client()
        client.config.on_change(lambda e: None, item_key="host")
        assert client.config._listeners[0][2] == "host"

    def test_fire_change_listeners_filters_by_config_key(self):
        client = _make_connected_client()
        events = []
        client.config.on_change(lambda e: events.append(e), config_key="db")
        client.config._fire_change_listeners(
            {"db": {"host": "old"}, "other": {"x": 1}},
            {"db": {"host": "new"}, "other": {"x": 2}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].config_key == "db"

    def test_fire_change_listeners_filters_by_item_key(self):
        client = _make_connected_client()
        events = []
        client.config.on_change(lambda e: events.append(e), item_key="host")
        client.config._fire_change_listeners(
            {"db": {"host": "old", "port": 1}},
            {"db": {"host": "new", "port": 2}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].item_key == "host"

    def test_no_change_fires_nothing(self):
        client = _make_connected_client()
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "same"}},
            {"db": {"host": "same"}},
            source="manual",
        )
        assert len(events) == 0

    def test_listener_exception_is_caught(self):
        client = _make_connected_client()
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
# 5. ConfigChangeEvent
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
# 6. Async refresh and change listeners
# ===================================================================


class TestAsyncRefresh:
    def test_refresh_requires_connect(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotConnectedError):
            asyncio.run(client.config.refresh())

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
            with patch("smplkit.config.models.AsyncConfig._build_chain", return_value=[
                {"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}
            ]):
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
            with patch("smplkit.config.models.AsyncConfig._build_chain", return_value=[
                {"id": "cfg-1", "values": {"host": "new-host"}, "environments": {}}
            ]):
                await client.config.refresh()

        asyncio.run(run())
        assert len(events) == 1
        assert events[0].source == "manual"


class TestAsyncChangeListeners:
    def test_on_change_registers_listener(self):
        client = _make_connected_async_client()
        client.config.on_change(lambda e: None)
        assert len(client.config._listeners) == 1

    def test_on_change_with_filters(self):
        client = _make_connected_async_client()
        client.config.on_change(lambda e: None, config_key="db", item_key="host")
        assert client.config._listeners[0][1] == "db"
        assert client.config._listeners[0][2] == "host"

    def test_fire_change_listeners(self):
        client = _make_connected_async_client()
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "old"}},
            {"db": {"host": "new"}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].config_key == "db"
        assert events[0].item_key == "host"

    def test_fire_change_listeners_filters_work(self):
        client = _make_connected_async_client()
        events = []
        client.config.on_change(lambda e: events.append(e), config_key="db", item_key="host")
        client.config._fire_change_listeners(
            {"db": {"host": "old", "port": 1}, "other": {"x": 1}},
            {"db": {"host": "new", "port": 2}, "other": {"x": 2}},
            source="manual",
        )
        assert len(events) == 1
        assert events[0].item_key == "host"

    def test_no_change_fires_nothing(self):
        client = _make_connected_async_client()
        events = []
        client.config.on_change(lambda e: events.append(e))
        client.config._fire_change_listeners(
            {"db": {"host": "same"}},
            {"db": {"host": "same"}},
            source="manual",
        )
        assert len(events) == 0

    def test_listener_exception_is_caught(self):
        client = _make_connected_async_client()
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
