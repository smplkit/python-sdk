"""Tests for Config and AsyncConfig model classes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from smplkit.config.models import AsyncConfig, Config, _AsyncConnectResult
from smplkit.config.runtime import ConfigRuntime


def _make_config(**overrides) -> Config:
    """Create a Config with sensible defaults."""
    defaults = {
        "id": "abc-123",
        "key": "test_config",
        "name": "Test Config",
        "description": "A test config",
        "parent": None,
        "values": {"retries": 3},
        "environments": {},
    }
    defaults.update(overrides)
    client = MagicMock()
    return Config(client, **defaults)


def _make_async_config(**overrides) -> AsyncConfig:
    """Create an AsyncConfig with sensible defaults."""
    defaults = {
        "id": "abc-123",
        "key": "test_config",
        "name": "Test Config",
        "description": "A test config",
        "parent": None,
        "values": {"retries": 3},
        "environments": {},
    }
    defaults.update(overrides)
    client = MagicMock()
    return AsyncConfig(client, **defaults)


class TestConfig:
    def test_attributes(self):
        cfg = _make_config()
        assert cfg.id == "abc-123"
        assert cfg.key == "test_config"
        assert cfg.name == "Test Config"
        assert cfg.description == "A test config"
        assert cfg.parent is None
        assert cfg.values == {"retries": 3}
        assert cfg.environments == {}

    def test_repr(self):
        cfg = _make_config()
        r = repr(cfg)
        assert "Config(" in r
        assert "abc-123" in r
        assert "test_config" in r
        assert "Test Config" in r

    def test_values_default_to_empty_dict(self):
        client = MagicMock()
        cfg = Config(client, id="x", key="k", name="n")
        assert cfg.values == {}
        assert cfg.environments == {}

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_builds_chain_no_parent(self, _mock_ws):
        mock_client = MagicMock()
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={"prod": {"values": {"a": 2}}},
        )
        runtime = cfg.connect("prod")
        assert runtime.get("a") == 2

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_fetch_chain_fn_calls_build_chain(self, _mock_ws):
        """The fetch_chain_fn closure passed to ConfigRuntime calls _build_chain."""
        mock_client = MagicMock()
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        runtime = cfg.connect("production")
        # Call the fetch_chain_fn — this exercises models.py line 223
        chain = runtime._fetch_chain_fn()
        assert isinstance(chain, list)
        assert chain[0]["id"] == "abc-123"

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_builds_chain_with_parent(self, _mock_ws):
        parent_cfg = _make_config(
            id="parent-1",
            key="parent",
            name="Parent",
            parent=None,
            values={"inherited": "yes", "shared": "parent_val"},
            environments={},
        )
        mock_client = MagicMock()
        mock_client.get.return_value = parent_cfg
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        child = Config(
            mock_client,
            id="child-1",
            key="child",
            name="Child",
            parent="parent-1",
            values={"shared": "child_val"},
            environments={},
        )

        runtime = child.connect("production")
        assert runtime.get("inherited") == "yes"
        assert runtime.get("shared") == "child_val"
        mock_client.get.assert_called_once_with(id="parent-1")


    def test_update_delegates_to_client(self):
        mock_client = MagicMock()
        updated = _make_config(name="Updated Name", description="new desc")
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Old Name",
            values={"a": 1},
            environments={},
        )
        cfg.update(name="Updated Name", description="new desc")
        mock_client._update_config.assert_called_once()
        assert cfg.name == "Updated Name"

    def test_set_values_base(self):
        mock_client = MagicMock()
        updated = _make_config(values={"x": 99})
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        cfg.set_values({"x": 99})
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["values"] == {"x": 99}

    def test_set_values_with_environment(self):
        mock_client = MagicMock()
        updated = _make_config(
            environments={"production": {"values": {"x": 99}}}
        )
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        cfg.set_values({"x": 99}, environment="production")
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["production"]["values"] == {"x": 99}

    def test_set_value_base(self):
        mock_client = MagicMock()
        updated = _make_config(values={"a": 1, "b": 2})
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        cfg.set_value("b", 2)
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["values"] == {"a": 1, "b": 2}

    def test_set_value_with_environment(self):
        mock_client = MagicMock()
        updated = _make_config(
            environments={"prod": {"values": {"flag": True}}}
        )
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={},
            environments={"prod": {"values": {"existing": 1}}},
        )
        cfg.set_value("flag", True, environment="prod")
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["prod"]["values"] == {
            "existing": 1,
            "flag": True,
        }


class TestAsyncConfig:
    def test_attributes(self):
        cfg = _make_async_config()
        assert cfg.id == "abc-123"
        assert cfg.key == "test_config"

    def test_repr(self):
        cfg = _make_async_config()
        r = repr(cfg)
        assert "AsyncConfig(" in r
        assert "abc-123" in r

    def test_update_delegates_to_client(self):
        mock_client = MagicMock()
        updated = _make_async_config(name="Updated Name")
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Old Name",
            values={"a": 1},
            environments={},
        )

        asyncio.run(cfg.update(name="Updated Name"))
        mock_client._update_config.assert_called_once()
        assert cfg.name == "Updated Name"

    def test_set_values_base(self):
        mock_client = MagicMock()
        updated = _make_async_config(values={"x": 99})
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        asyncio.run(cfg.set_values({"x": 99}))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["values"] == {"x": 99}

    def test_set_values_with_environment(self):
        mock_client = MagicMock()
        updated = _make_async_config(
            environments={"production": {"values": {"x": 99}}}
        )
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        asyncio.run(cfg.set_values({"x": 99}, environment="production"))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["production"]["values"] == {"x": 99}

    def test_set_value_base(self):
        mock_client = MagicMock()
        updated = _make_async_config(values={"a": 1, "b": 2})
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )
        asyncio.run(cfg.set_value("b", 2))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["values"] == {"a": 1, "b": 2}

    def test_set_value_with_environment(self):
        mock_client = MagicMock()
        updated = _make_async_config(
            environments={"prod": {"values": {"flag": True}}}
        )
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={},
            environments={"prod": {"values": {"existing": 1}}},
        )
        asyncio.run(cfg.set_value("flag", True, environment="prod"))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["prod"]["values"] == {
            "existing": 1,
            "flag": True,
        }

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_builds_chain_with_parent(self, _mock_ws):
        parent_cfg = _make_async_config(
            id="parent-1",
            key="parent",
            name="Parent",
            parent=None,
            values={"inherited": "yes", "shared": "parent_val"},
            environments={},
        )
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=parent_cfg)
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        child = AsyncConfig(
            mock_client,
            id="child-1",
            key="child",
            name="Child",
            parent="parent-1",
            values={"shared": "child_val"},
            environments={},
        )

        async def _run():
            runtime = await child.connect("production")
            assert runtime.get("inherited") == "yes"
            assert runtime.get("shared") == "child_val"

        asyncio.run(_run())
        mock_client.get.assert_called_once_with(id="parent-1")

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_no_parent(self, _mock_ws):
        mock_client = MagicMock()
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={"prod": {"values": {"a": 2}}},
        )

        async def _run():
            runtime = await cfg.connect("prod")
            assert runtime.get("a") == 2

        asyncio.run(_run())

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_fetch_chain_fn_calls_build_chain(self, _mock_ws):
        """The async fetch_chain_fn closure calls _build_chain (returns coroutine)."""
        mock_client = MagicMock()
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )

        async def _run():
            runtime = await cfg.connect("production")
            # Call the fetch_chain_fn — this exercises models.py line 439
            result = runtime._fetch_chain_fn()
            # For async config, _fetch_chain returns a coroutine
            if asyncio.iscoroutine(result):
                chain = await result
            else:
                chain = result
            assert isinstance(chain, list)
            assert chain[0]["id"] == "abc-123"

        asyncio.run(_run())

    @patch.object(ConfigRuntime, "_start_ws_thread")
    def test_connect_as_async_context_manager(self, _mock_ws):
        mock_client = MagicMock()
        mock_client._parent._api_key = "sk_test"
        mock_client._parent._http_client._base_url = "https://config.smplkit.com"

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            values={"a": 1},
            environments={},
        )

        async def _run():
            async with cfg.connect("production") as runtime:
                assert runtime.get("a") == 1
            assert runtime._closed is True

        asyncio.run(_run())


class TestAsyncConnectResult:
    def test_await_returns_runtime(self):
        async def fake_coro():
            return "runtime_obj"

        result = _AsyncConnectResult(fake_coro())

        async def _run():
            val = await result
            assert val == "runtime_obj"

        asyncio.run(_run())

    def test_async_with_returns_runtime_and_closes(self):
        mock_runtime = MagicMock()
        mock_runtime.close = AsyncMock()

        async def fake_coro():
            return mock_runtime

        result = _AsyncConnectResult(fake_coro())

        async def _run():
            async with result as rt:
                assert rt is mock_runtime
            mock_runtime.close.assert_called_once()

        asyncio.run(_run())

    def test_async_with_no_runtime(self):
        """__aexit__ with no runtime (e.g. if __aenter__ wasn't called) should not raise."""
        async def fake_coro():
            return MagicMock()

        result = _AsyncConnectResult(fake_coro())

        async def _run():
            # Call __aexit__ directly without __aenter__
            await result.__aexit__(None, None, None)

        asyncio.run(_run())
