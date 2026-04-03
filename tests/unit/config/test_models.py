"""Tests for Config and AsyncConfig model classes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from smplkit.config.models import AsyncConfig, Config


def _make_config(**overrides) -> Config:
    """Create a Config with sensible defaults."""
    defaults = {
        "id": "abc-123",
        "key": "test_config",
        "name": "Test Config",
        "description": "A test config",
        "parent": None,
        "items": {"retries": {"value": 3, "type": "NUMBER"}},
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
        "items": {"retries": {"value": 3, "type": "NUMBER"}},
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
        assert cfg.items == {"retries": 3}
        assert cfg.items_raw == {"retries": {"value": 3, "type": "NUMBER"}}
        assert cfg.environments == {}

    def test_repr(self):
        cfg = _make_config()
        r = repr(cfg)
        assert "Config(" in r
        assert "abc-123" in r
        assert "test_config" in r
        assert "Test Config" in r

    def test_items_default_to_empty_dict(self):
        client = MagicMock()
        cfg = Config(client, id="x", key="k", name="n")
        assert cfg.items == {}
        assert cfg.environments == {}

    def test_build_chain_no_parent(self):
        cfg = _make_config()
        chain = cfg._build_chain()
        assert len(chain) == 1
        assert chain[0]["id"] == "abc-123"

    def test_build_chain_with_parent(self):
        parent_cfg = _make_config(
            id="parent-1",
            key="parent",
            name="Parent",
            parent=None,
            items={"inherited": {"value": "yes"}, "shared": {"value": "parent_val"}},
            environments={},
        )
        mock_client = MagicMock()
        mock_client.get.return_value = parent_cfg

        child = Config(
            mock_client,
            id="child-1",
            key="child",
            name="Child",
            parent="parent-1",
            items={"shared": {"value": "child_val"}},
            environments={},
        )

        chain = child._build_chain()
        assert len(chain) == 2
        assert chain[0]["id"] == "child-1"
        assert chain[1]["id"] == "parent-1"
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
            items={"a": {"value": 1}},
            environments={},
        )
        cfg.update(name="Updated Name", description="new desc")
        mock_client._update_config.assert_called_once()
        assert cfg.name == "Updated Name"

    def test_set_items_base(self):
        mock_client = MagicMock()
        updated = _make_config(items={"x": {"value": 99}})
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={"a": {"value": 1}},
            environments={},
        )
        cfg.set_items({"x": {"value": 99}})
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["items"] == {"x": {"value": 99}}

    def test_set_items_with_environment(self):
        mock_client = MagicMock()
        updated = _make_config(environments={"production": {"values": {"x": 99}}})
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={"a": {"value": 1}},
            environments={},
        )
        cfg.set_items({"x": 99}, environment="production")
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["production"]["values"] == {"x": 99}

    def test_set_value_base(self):
        mock_client = MagicMock()
        updated = _make_config(items={"a": {"value": 1}, "b": {"value": 2}})
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={"a": {"value": 1}},
            environments={},
        )
        cfg.set_value("b", 2)
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["items"] == {"a": {"value": 1}, "b": {"value": 2}}

    def test_set_value_with_environment(self):
        mock_client = MagicMock()
        updated = _make_config(environments={"prod": {"values": {"flag": True}}})
        mock_client._update_config.return_value = updated

        cfg = Config(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={},
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
        assert cfg.items == {"retries": 3}
        assert cfg.items_raw == {"retries": {"value": 3, "type": "NUMBER"}}

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
            items={"a": {"value": 1}},
            environments={},
        )

        asyncio.run(cfg.update(name="Updated Name"))
        mock_client._update_config.assert_called_once()
        assert cfg.name == "Updated Name"

    def test_set_items_base(self):
        mock_client = MagicMock()
        updated = _make_async_config(items={"x": {"value": 99}})
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={"a": {"value": 1}},
            environments={},
        )
        asyncio.run(cfg.set_items({"x": {"value": 99}}))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["items"] == {"x": {"value": 99}}

    def test_set_items_with_environment(self):
        mock_client = MagicMock()
        updated = _make_async_config(environments={"production": {"values": {"x": 99}}})
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={"a": {"value": 1}},
            environments={},
        )
        asyncio.run(cfg.set_items({"x": 99}, environment="production"))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["production"]["values"] == {"x": 99}

    def test_set_value_base(self):
        mock_client = MagicMock()
        updated = _make_async_config(items={"a": {"value": 1}, "b": {"value": 2}})
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={"a": {"value": 1}},
            environments={},
        )
        asyncio.run(cfg.set_value("b", 2))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["items"] == {"a": {"value": 1}, "b": {"value": 2}}

    def test_set_value_with_environment(self):
        mock_client = MagicMock()
        updated = _make_async_config(environments={"prod": {"values": {"flag": True}}})
        mock_client._update_config = AsyncMock(return_value=updated)

        cfg = AsyncConfig(
            mock_client,
            id="abc-123",
            key="test_config",
            name="Test",
            items={},
            environments={"prod": {"values": {"existing": 1}}},
        )
        asyncio.run(cfg.set_value("flag", True, environment="prod"))
        call_kwargs = mock_client._update_config.call_args[1]
        assert call_kwargs["environments"]["prod"]["values"] == {
            "existing": 1,
            "flag": True,
        }

    def test_build_chain_with_parent(self):
        parent_cfg = _make_async_config(
            id="parent-1",
            key="parent",
            name="Parent",
            parent=None,
            items={"inherited": {"value": "yes"}},
            environments={},
        )
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=parent_cfg)

        child = AsyncConfig(
            mock_client,
            id="child-1",
            key="child",
            name="Child",
            parent="parent-1",
            items={"shared": {"value": "child_val"}},
            environments={},
        )

        async def _run():
            chain = await child._build_chain()
            assert len(chain) == 2
            assert chain[0]["id"] == "child-1"
            assert chain[1]["id"] == "parent-1"

        asyncio.run(_run())
        mock_client.get.assert_called_once_with(id="parent-1")

    def test_build_chain_no_parent(self):
        cfg = _make_async_config()

        async def _run():
            chain = await cfg._build_chain()
            assert len(chain) == 1
            assert chain[0]["id"] == "abc-123"

        asyncio.run(_run())
