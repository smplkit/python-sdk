"""Tests for smplkit.management.models — all active-record model classes."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from smplkit.management.models import (
    AccountSettings,
    AsyncAccountSettings,
    AsyncContextEntity,
    AsyncContextType,
    AsyncEnvironment,
    ContextEntity,
    ContextType,
    Environment,
    _AccountSettingsBase,
    _ContextTypeBase,
    _EnvironmentBase,
)
from smplkit.management.types import EnvironmentClassification


# ---------------------------------------------------------------------------
# _EnvironmentBase / Environment / AsyncEnvironment
# ---------------------------------------------------------------------------


class TestEnvironmentBase:
    def test_default_init(self):
        env = _EnvironmentBase.__new__(_EnvironmentBase)
        _EnvironmentBase.__init__(env, name="production")
        assert env.id is None
        assert env.name == "production"
        assert env.color is None
        assert env.classification == EnvironmentClassification.STANDARD
        assert env.created_at is None
        assert env.updated_at is None

    def test_full_init(self):
        env = _EnvironmentBase.__new__(_EnvironmentBase)
        _EnvironmentBase.__init__(
            env,
            id="env-1",
            name="staging",
            color="#00ff00",
            classification=EnvironmentClassification.AD_HOC,
            created_at="2026-01-01",
            updated_at="2026-01-02",
        )
        assert env.id == "env-1"
        assert env.color == "#00ff00"
        assert env.classification == EnvironmentClassification.AD_HOC

    def test_repr(self):
        env = Environment(name="production", classification=EnvironmentClassification.STANDARD)
        r = repr(env)
        assert "Environment" in r
        assert "production" in r
        assert "STANDARD" in r

    def test_apply(self):
        env1 = Environment(name="production", id="e-1", created_at="2026-01-01")
        env2 = Environment(name="staging", id="e-2", color="#ff0000", updated_at="2026-02-01")
        env1._apply(env2)
        assert env1.name == "staging"
        assert env1.id == "e-2"
        assert env1.color == "#ff0000"
        assert env1.updated_at == "2026-02-01"


class TestEnvironmentSave:
    def test_save_no_client_raises(self):
        env = Environment(name="production")
        with pytest.raises(RuntimeError, match="without a client"):
            env.save()

    def test_save_creates_when_no_created_at(self):
        mock_client = MagicMock()
        created = Environment(mock_client, id="env-1", name="production", created_at="2026-01-01")
        mock_client._create.return_value = created
        env = Environment(mock_client, name="production")
        env.save()
        mock_client._create.assert_called_once_with(env)
        assert env.id == "env-1"

    def test_save_updates_when_created_at_is_set(self):
        mock_client = MagicMock()
        updated = Environment(mock_client, id="env-1", name="updated-name", created_at="2026-01-01")
        mock_client._update.return_value = updated
        env = Environment(mock_client, id="env-1", name="production", created_at="2026-01-01")
        env.save()
        mock_client._update.assert_called_once_with(env)
        assert env.name == "updated-name"


class TestAsyncEnvironmentSave:
    def test_save_no_client_raises(self):
        env = AsyncEnvironment(name="production")
        with pytest.raises(RuntimeError, match="without a client"):
            asyncio.run(env.save())

    def test_save_creates(self):
        async def _run():
            mock_client = MagicMock()
            created = AsyncEnvironment(mock_client, id="env-1", name="production", created_at="2026-01-01")
            mock_client._create = AsyncMockReturning(created)
            env = AsyncEnvironment(mock_client, name="production")
            await env.save()
            assert env.id == "env-1"

        asyncio.run(_run())

    def test_save_updates(self):
        async def _run():
            mock_client = MagicMock()
            updated = AsyncEnvironment(mock_client, id="e-1", name="new-name", created_at="2026-01-01")

            async def fake_create(arg):
                return updated

            async def fake_update(arg):
                return updated

            mock_client._create = fake_create
            mock_client._update = fake_update

            env = AsyncEnvironment(mock_client, id="e-1", name="production", created_at="2026-01-01")
            await env.save()
            assert env.name == "new-name"

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# _ContextTypeBase / ContextType / AsyncContextType
# ---------------------------------------------------------------------------


class TestContextTypeBase:
    def test_default_init(self):
        ct = _ContextTypeBase.__new__(_ContextTypeBase)
        _ContextTypeBase.__init__(ct, name="user")
        assert ct.id is None
        assert ct.name == "user"
        assert ct.attributes == {}
        assert ct.created_at is None

    def test_init_with_attributes(self):
        ct = _ContextTypeBase.__new__(_ContextTypeBase)
        _ContextTypeBase.__init__(ct, name="user", attributes={"plan": {"type": "string"}})
        assert ct.attributes == {"plan": {"type": "string"}}

    def test_add_attribute(self):
        ct = ContextType(name="user")
        ct.add_attribute("plan", type="string", required=True)
        assert ct.attributes["plan"] == {"type": "string", "required": True}

    def test_remove_attribute(self):
        ct = ContextType(name="user", attributes={"plan": {}, "region": {}})
        ct.remove_attribute("plan")
        assert "plan" not in ct.attributes
        assert "region" in ct.attributes

    def test_remove_attribute_missing_key_no_error(self):
        ct = ContextType(name="user")
        ct.remove_attribute("nonexistent")  # should not raise

    def test_update_attribute(self):
        ct = ContextType(name="user", attributes={"plan": {"type": "string"}})
        ct.update_attribute("plan", type="integer", required=False)
        assert ct.attributes["plan"] == {"type": "integer", "required": False}

    def test_repr(self):
        ct = ContextType(id="ct-1", name="user")
        r = repr(ct)
        assert "ContextType" in r
        assert "ct-1" in r
        assert "user" in r

    def test_apply(self):
        ct1 = ContextType(id="ct-1", name="user", attributes={"a": {}})
        ct2 = ContextType(id="ct-2", name="account", attributes={"b": {}}, created_at="2026-01-01")
        ct1._apply(ct2)
        assert ct1.id == "ct-2"
        assert ct1.name == "account"
        assert ct1.attributes == {"b": {}}
        assert ct1.created_at == "2026-01-01"


class TestContextTypeSave:
    def test_save_no_client_raises(self):
        ct = ContextType(name="user")
        with pytest.raises(RuntimeError, match="without a client"):
            ct.save()

    def test_save_creates_when_no_created_at(self):
        mock_client = MagicMock()
        result = ContextType(mock_client, id="ct-1", name="user", created_at="2026-01-01")
        mock_client._create.return_value = result
        ct = ContextType(mock_client, name="user")
        ct.save()
        mock_client._create.assert_called_once_with(ct)
        assert ct.id == "ct-1"

    def test_save_updates_when_created_at_set(self):
        mock_client = MagicMock()
        result = ContextType(mock_client, id="ct-1", name="updated", created_at="2026-01-01")
        mock_client._update.return_value = result
        ct = ContextType(mock_client, id="ct-1", name="user", created_at="2026-01-01")
        ct.save()
        mock_client._update.assert_called_once_with(ct)
        assert ct.name == "updated"


class TestAsyncContextTypeSave:
    def test_save_no_client_raises(self):
        ct = AsyncContextType(name="user")
        with pytest.raises(RuntimeError, match="without a client"):
            asyncio.run(ct.save())

    def test_save_creates(self):
        async def _run():
            mock_client = MagicMock()
            result = AsyncContextType(mock_client, id="ct-1", name="user", created_at="2026-01-01")

            async def fake_create(arg):
                return result

            mock_client._create = fake_create
            ct = AsyncContextType(mock_client, name="user")
            await ct.save()
            assert ct.id == "ct-1"

        asyncio.run(_run())

    def test_save_updates(self):
        async def _run():
            mock_client = MagicMock()
            result = AsyncContextType(mock_client, id="ct-1", name="updated", created_at="2026-01-01")

            async def fake_update(arg):
                return result

            mock_client._update = fake_update
            ct = AsyncContextType(mock_client, id="ct-1", name="user", created_at="2026-01-01")
            await ct.save()
            assert ct.name == "updated"

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# _ContextEntityBase / ContextEntity / AsyncContextEntity
# ---------------------------------------------------------------------------


class TestContextEntityBase:
    def test_init(self):
        entity = ContextEntity(type="user", key="u-1", name="Alice", attributes={"plan": "pro"})
        assert entity.type == "user"
        assert entity.key == "u-1"
        assert entity.name == "Alice"
        assert entity.attributes == {"plan": "pro"}

    def test_default_init(self):
        entity = ContextEntity(type="user", key="u-1")
        assert entity.name is None
        assert entity.attributes == {}
        assert entity.created_at is None
        assert entity.updated_at is None

    def test_id_property(self):
        entity = ContextEntity(type="user", key="u-42")
        assert entity.id == "user:u-42"

    def test_repr(self):
        entity = ContextEntity(type="account", key="acme")
        r = repr(entity)
        assert "ContextEntity" in r
        assert "account" in r
        assert "acme" in r

    def test_async_entity(self):
        entity = AsyncContextEntity(type="user", key="u-1", created_at="2026-01-01")
        assert entity.id == "user:u-1"
        assert entity.created_at == "2026-01-01"


# ---------------------------------------------------------------------------
# _AccountSettingsBase / AccountSettings / AsyncAccountSettings
# ---------------------------------------------------------------------------


class TestAccountSettingsBase:
    def test_default_init(self):
        settings = _AccountSettingsBase.__new__(_AccountSettingsBase)
        _AccountSettingsBase.__init__(settings)
        assert settings._data == {}

    def test_init_with_data(self):
        settings = _AccountSettingsBase.__new__(_AccountSettingsBase)
        _AccountSettingsBase.__init__(settings, data={"environment_order": ["prod", "staging"]})
        assert settings._data == {"environment_order": ["prod", "staging"]}

    def test_raw_getter(self):
        settings = AccountSettings(data={"foo": "bar"})
        assert settings.raw == {"foo": "bar"}

    def test_raw_setter(self):
        settings = AccountSettings(data={"foo": "bar"})
        settings.raw = {"baz": "qux"}
        assert settings._data == {"baz": "qux"}

    def test_environment_order_getter_empty(self):
        settings = AccountSettings()
        assert settings.environment_order == []

    def test_environment_order_getter_with_value(self):
        settings = AccountSettings(data={"environment_order": ["prod", "staging"]})
        assert settings.environment_order == ["prod", "staging"]

    def test_environment_order_setter(self):
        settings = AccountSettings()
        settings.environment_order = ["prod", "staging", "dev"]
        assert settings._data["environment_order"] == ["prod", "staging", "dev"]

    def test_repr(self):
        settings = AccountSettings(data={"foo": 1})
        r = repr(settings)
        assert "AccountSettings" in r

    def test_apply(self):
        s1 = AccountSettings(data={"foo": 1})
        s2 = AccountSettings(data={"bar": 2})
        s1._apply(s2)
        assert s1._data == {"bar": 2}


class TestAccountSettingsSave:
    def test_save_no_client_raises(self):
        settings = AccountSettings(data={"foo": 1})
        with pytest.raises(RuntimeError, match="without a client"):
            settings.save()

    def test_save_calls_client_save(self):
        mock_client = MagicMock()
        updated = AccountSettings(mock_client, data={"environment_order": ["prod"]})
        mock_client._save.return_value = updated
        settings = AccountSettings(mock_client, data={"environment_order": []})
        settings.save()
        mock_client._save.assert_called_once_with({"environment_order": []})
        assert settings._data == {"environment_order": ["prod"]}


class TestAsyncAccountSettingsSave:
    def test_save_no_client_raises(self):
        settings = AsyncAccountSettings(data={"foo": 1})
        with pytest.raises(RuntimeError, match="without a client"):
            asyncio.run(settings.save())

    def test_save_calls_client_save(self):
        async def _run():
            mock_client = MagicMock()
            updated = AsyncAccountSettings(mock_client, data={"environment_order": ["prod"]})

            async def fake_save(data):
                return updated

            mock_client._save = fake_save
            settings = AsyncAccountSettings(mock_client, data={})
            await settings.save()
            assert settings._data == {"environment_order": ["prod"]}

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Helper for async tests
# ---------------------------------------------------------------------------


class AsyncMockReturning:
    """Minimal async callable returning a fixed value."""

    def __init__(self, value):
        self._value = value

    async def __call__(self, *args, **kwargs):
        return self._value
