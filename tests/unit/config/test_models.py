"""Tests for Config and AsyncConfig model classes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from smplkit.config.models import AsyncConfig, Config


def _make_config(**overrides) -> Config:
    """Create a Config with sensible defaults."""
    defaults = {
        "id": "test_config",
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
        "id": "test_config",
        "name": "Test Config",
        "description": "A test config",
        "parent": None,
        "items": {"retries": {"value": 3, "type": "NUMBER"}},
        "environments": {},
    }
    defaults.update(overrides)
    client = MagicMock()
    return AsyncConfig(client, **defaults)


# ===================================================================
# Config — attributes and basics
# ===================================================================


class TestConfigAttributes:
    def test_attributes(self):
        cfg = _make_config()
        assert cfg.id == "test_config"
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
        assert "test_config" in r
        assert "Test Config" in r

    def test_items_default_to_empty_dict(self):
        client = MagicMock()
        cfg = Config(client, id="x", name="n")
        assert cfg.items == {}
        assert cfg.environments == {}

    def test_id_can_be_none(self):
        client = MagicMock()
        cfg = Config(client, id=None, name="n")
        assert cfg.id is None


# ===================================================================
# Config — settable items property
# ===================================================================


class TestConfigSettableItems:
    def test_set_plain_values(self):
        cfg = _make_config()
        cfg.items = {"host": "localhost", "port": 5432}
        assert cfg.items == {"host": "localhost", "port": 5432}
        # Internally wrapped
        assert cfg._items_raw == {"host": {"value": "localhost"}, "port": {"value": 5432}}

    def test_set_already_wrapped_values(self):
        cfg = _make_config()
        cfg.items = {"host": {"value": "localhost", "type": "STRING"}}
        assert cfg.items == {"host": "localhost"}
        assert cfg._items_raw == {"host": {"value": "localhost", "type": "STRING"}}

    def test_set_mixed_values(self):
        cfg = _make_config()
        cfg.items = {"host": "localhost", "port": {"value": 5432}}
        assert cfg.items == {"host": "localhost", "port": 5432}

    def test_items_raw_returns_copy(self):
        cfg = _make_config()
        raw = cfg.items_raw
        raw["new_key"] = {"value": "should not leak"}
        assert "new_key" not in cfg.items_raw


# ===================================================================
# Config — save()
# ===================================================================


class TestConfigSave:
    def test_save_creates_when_created_at_is_none(self):
        mock_client = MagicMock()
        created = _make_config(id="new-id", name="Created Config")
        mock_client._create_config.return_value = created

        cfg = Config(mock_client, id="test", name="Test")
        cfg.save()

        mock_client._create_config.assert_called_once_with(cfg)
        assert cfg.id == "new-id"
        assert cfg.name == "Created Config"

    def test_save_updates_when_created_at_is_set(self):
        import datetime

        mock_client = MagicMock()
        updated = _make_config(id="test_config", name="Updated Config")
        mock_client._update_config_from_model.return_value = updated

        cfg = Config(mock_client, id="test_config", name="Old Name")
        cfg.created_at = datetime.datetime(2025, 1, 1)
        cfg.save()

        mock_client._update_config_from_model.assert_called_once_with(cfg)
        assert cfg.name == "Updated Config"


# ===================================================================
# Config — _apply()
# ===================================================================


class TestConfigApply:
    def test_apply_copies_all_fields(self):
        import datetime

        cfg = _make_config(id="old-id", name="Old")
        other = _make_config(
            id="new-id",
            name="New",
            description="New desc",
            parent="parent-id",
            items={"host": {"value": "h"}},
            environments={"prod": {"values": {"host": "prod-h"}}},
        )
        other.created_at = datetime.datetime(2025, 1, 1)
        other.updated_at = datetime.datetime(2025, 6, 1)

        cfg._apply(other)

        assert cfg.id == "new-id"
        assert cfg.name == "New"
        assert cfg.description == "New desc"
        assert cfg.parent == "parent-id"
        assert cfg.items == {"host": "h"}
        assert cfg.environments == {"prod": {"values": {"host": "prod-h"}}}
        assert cfg.created_at == datetime.datetime(2025, 1, 1)
        assert cfg.updated_at == datetime.datetime(2025, 6, 1)

    def test_apply_copies_items_raw(self):
        cfg = _make_config()
        other = _make_config(items={"x": {"value": 99, "type": "NUMBER"}})
        cfg._apply(other)
        assert cfg._items_raw == {"x": {"value": 99, "type": "NUMBER"}}


# ===================================================================
# Config — _build_chain
# ===================================================================


class TestConfigBuildChain:
    def test_build_chain_no_parent(self):
        cfg = _make_config()
        chain = cfg._build_chain()
        assert len(chain) == 1
        assert chain[0]["id"] == "test_config"

    def test_build_chain_with_parent(self):
        parent_cfg = _make_config(
            id="parent-1",
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
            name="Child",
            parent="parent-1",
            items={"shared": {"value": "child_val"}},
            environments={},
        )

        chain = child._build_chain()
        assert len(chain) == 2
        assert chain[0]["id"] == "child-1"
        assert chain[1]["id"] == "parent-1"
        mock_client.get.assert_called_once_with("parent-1")

    def test_build_chain_with_configs_list(self):
        """When a configs list is provided, parents are looked up by ID without calling get()."""
        parent_cfg = _make_config(
            id="parent-1",
            name="Parent",
            parent=None,
            items={"inherited": {"value": "yes"}},
            environments={},
        )
        mock_client = MagicMock()

        child = Config(
            mock_client,
            id="child-1",
            name="Child",
            parent="parent-1",
            items={"shared": {"value": "child_val"}},
            environments={},
        )

        chain = child._build_chain(configs=[parent_cfg, child])
        assert len(chain) == 2
        assert chain[0]["id"] == "child-1"
        assert chain[1]["id"] == "parent-1"
        mock_client.get.assert_not_called()


# ===================================================================
# AsyncConfig — attributes and basics
# ===================================================================


class TestAsyncConfigAttributes:
    def test_attributes(self):
        cfg = _make_async_config()
        assert cfg.id == "test_config"
        assert cfg.items == {"retries": 3}
        assert cfg.items_raw == {"retries": {"value": 3, "type": "NUMBER"}}

    def test_repr(self):
        cfg = _make_async_config()
        r = repr(cfg)
        assert "AsyncConfig(" in r
        assert "test_config" in r

    def test_id_can_be_none(self):
        client = MagicMock()
        cfg = AsyncConfig(client, id=None, name="n")
        assert cfg.id is None


# ===================================================================
# AsyncConfig — settable items property
# ===================================================================


class TestAsyncConfigSettableItems:
    def test_set_plain_values(self):
        cfg = _make_async_config()
        cfg.items = {"host": "localhost", "port": 5432}
        assert cfg.items == {"host": "localhost", "port": 5432}
        assert cfg._items_raw == {"host": {"value": "localhost"}, "port": {"value": 5432}}

    def test_set_already_wrapped_values(self):
        cfg = _make_async_config()
        cfg.items = {"host": {"value": "localhost", "type": "STRING"}}
        assert cfg.items == {"host": "localhost"}
        assert cfg._items_raw == {"host": {"value": "localhost", "type": "STRING"}}

    def test_set_mixed_values(self):
        cfg = _make_async_config()
        cfg.items = {"host": "localhost", "port": {"value": 5432}}
        assert cfg.items == {"host": "localhost", "port": 5432}

    def test_items_raw_returns_copy(self):
        cfg = _make_async_config()
        raw = cfg.items_raw
        raw["new_key"] = {"value": "should not leak"}
        assert "new_key" not in cfg.items_raw


# ===================================================================
# AsyncConfig — save()
# ===================================================================


class TestAsyncConfigSave:
    def test_save_creates_when_created_at_is_none(self):
        mock_client = MagicMock()
        created = _make_async_config(id="new-id", name="Created Config")
        mock_client._create_config = AsyncMock(return_value=created)

        cfg = AsyncConfig(mock_client, id="test", name="Test")
        asyncio.run(cfg.save())

        mock_client._create_config.assert_called_once_with(cfg)
        assert cfg.id == "new-id"
        assert cfg.name == "Created Config"

    def test_save_updates_when_created_at_is_set(self):
        import datetime

        mock_client = MagicMock()
        updated = _make_async_config(id="test_config", name="Updated Config")
        mock_client._update_config_from_model = AsyncMock(return_value=updated)

        cfg = AsyncConfig(mock_client, id="test_config", name="Old Name")
        cfg.created_at = datetime.datetime(2025, 1, 1)
        asyncio.run(cfg.save())

        mock_client._update_config_from_model.assert_called_once_with(cfg)
        assert cfg.name == "Updated Config"


# ===================================================================
# AsyncConfig — _apply()
# ===================================================================


class TestAsyncConfigApply:
    def test_apply_copies_all_fields(self):
        import datetime

        cfg = _make_async_config(id="old-id", name="Old")
        other = _make_async_config(
            id="new-id",
            name="New",
            description="New desc",
            parent="parent-id",
            items={"host": {"value": "h"}},
            environments={"prod": {"values": {"host": "prod-h"}}},
        )
        other.created_at = datetime.datetime(2025, 1, 1)
        other.updated_at = datetime.datetime(2025, 6, 1)

        cfg._apply(other)

        assert cfg.id == "new-id"
        assert cfg.name == "New"
        assert cfg.description == "New desc"
        assert cfg.parent == "parent-id"
        assert cfg.items == {"host": "h"}
        assert cfg.environments == {"prod": {"values": {"host": "prod-h"}}}
        assert cfg.created_at == datetime.datetime(2025, 1, 1)
        assert cfg.updated_at == datetime.datetime(2025, 6, 1)

    def test_apply_copies_items_raw(self):
        cfg = _make_async_config()
        other = _make_async_config(items={"x": {"value": 99, "type": "NUMBER"}})
        cfg._apply(other)
        assert cfg._items_raw == {"x": {"value": 99, "type": "NUMBER"}}


# ===================================================================
# AsyncConfig — _build_chain
# ===================================================================


class TestAsyncConfigBuildChain:
    def test_build_chain_with_parent(self):
        parent_cfg = _make_async_config(
            id="parent-1",
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
        mock_client.get.assert_called_once_with("parent-1")

    def test_build_chain_with_configs_list(self):
        """When a configs list is provided, parents are looked up by ID without calling get()."""
        parent_cfg = _make_async_config(
            id="parent-1",
            name="Parent",
            parent=None,
            items={"inherited": {"value": "yes"}},
            environments={},
        )
        mock_client = MagicMock()

        child = AsyncConfig(
            mock_client,
            id="child-1",
            name="Child",
            parent="parent-1",
            items={"shared": {"value": "child_val"}},
            environments={},
        )

        async def _run():
            chain = await child._build_chain(configs=[parent_cfg, child])
            assert len(chain) == 2
            assert chain[0]["id"] == "child-1"
            assert chain[1]["id"] == "parent-1"

        asyncio.run(_run())
        mock_client.get.assert_not_called()

    def test_build_chain_no_parent(self):
        cfg = _make_async_config()

        async def _run():
            chain = await cfg._build_chain()
            assert len(chain) == 1
            assert chain[0]["id"] == "test_config"

        asyncio.run(_run())
