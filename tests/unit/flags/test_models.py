"""Tests for the unified Flag model hierarchy (sync and async variants)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from smplkit.flags.models import (
    AsyncBooleanFlag,
    AsyncFlag,
    AsyncJsonFlag,
    AsyncNumberFlag,
    AsyncStringFlag,
    BooleanFlag,
    Flag,
    JsonFlag,
    NumberFlag,
    StringFlag,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flag(cls=Flag, client=None, **overrides):
    defaults = {
        "id": "flag-id-1",
        "key": "test-flag",
        "name": "Test Flag",
        "type": "BOOLEAN",
        "default": False,
        "values": [{"name": "True", "value": True}],
        "description": "A test flag",
        "environments": {"staging": {"enabled": True, "rules": []}},
    }
    defaults.update(overrides)
    client = client or MagicMock()
    return cls(client, **defaults)


# ===========================================================================
# Flag (sync base)
# ===========================================================================


class TestFlag:
    def test_properties(self):
        flag = _make_flag()
        assert flag.id == "flag-id-1"
        assert flag.key == "test-flag"
        assert flag.name == "Test Flag"
        assert flag.type == "BOOLEAN"
        assert flag.default is False
        assert flag.description == "A test flag"
        assert flag.values == [{"name": "True", "value": True}]
        assert flag.environments == {"staging": {"enabled": True, "rules": []}}

    def test_defaults(self):
        client = MagicMock()
        flag = Flag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.id is None
        assert flag.values == []
        assert flag.description is None
        assert flag.environments == {}
        assert flag.created_at is None
        assert flag.updated_at is None

    def test_repr(self):
        flag = _make_flag()
        r = repr(flag)
        assert "test-flag" in r
        assert "BOOLEAN" in r

    # ------------------------------------------------------------------
    # save() — create path (id is None)
    # ------------------------------------------------------------------

    def test_save_creates_when_id_is_none(self):
        client = MagicMock()
        flag = Flag(client, key="new-flag", name="New", type="BOOLEAN", default=False)
        created = Flag(client, id="new-id", key="new-flag", name="New", type="BOOLEAN", default=False)
        client._create_flag.return_value = created

        flag.save()

        client._create_flag.assert_called_once_with(flag)
        assert flag.id == "new-id"

    # ------------------------------------------------------------------
    # save() — update path (id is set)
    # ------------------------------------------------------------------

    def test_save_updates_when_id_is_set(self):
        client = MagicMock()
        flag = Flag(client, id="existing-id", key="flag", name="Old", type="BOOLEAN", default=False)
        updated = Flag(client, id="existing-id", key="flag", name="Updated", type="BOOLEAN", default=True)
        client._update_flag.return_value = updated

        flag.save()

        client._update_flag.assert_called_once_with(flag=flag)
        assert flag.name == "Updated"
        assert flag.default is True

    # ------------------------------------------------------------------
    # _apply
    # ------------------------------------------------------------------

    def test_apply_copies_all_fields(self):
        client = MagicMock()
        flag = Flag(client, key="k", name="n", type="BOOLEAN", default=False)
        other = Flag(
            client,
            id="new-id",
            key="new-key",
            name="new-name",
            type="STRING",
            default="hello",
            values=[{"name": "v", "value": "v"}],
            description="desc",
            environments={"prod": {"enabled": True}},
            created_at="2024-01-01",
            updated_at="2024-06-01",
        )
        flag._apply(other)
        assert flag.id == "new-id"
        assert flag.key == "new-key"
        assert flag.name == "new-name"
        assert flag.type == "STRING"
        assert flag.default == "hello"
        assert flag.values == [{"name": "v", "value": "v"}]
        assert flag.description == "desc"
        assert flag.environments == {"prod": {"enabled": True}}
        assert flag.created_at == "2024-01-01"
        assert flag.updated_at == "2024-06-01"

    # ------------------------------------------------------------------
    # addRule — local mutation
    # ------------------------------------------------------------------

    def test_addRule_appends_to_environment(self):
        flag = _make_flag(environments={"staging": {"enabled": True, "rules": []}})
        rule = {"environment": "staging", "logic": {"==": [1, 1]}, "value": True, "description": "always on"}
        result = flag.addRule(rule)

        # Returns self for chaining
        assert result is flag
        # Rule added without environment key
        assert len(flag.environments["staging"]["rules"]) == 1
        added = flag.environments["staging"]["rules"][0]
        assert "environment" not in added
        assert added["logic"] == {"==": [1, 1]}
        assert added["value"] is True
        assert added["description"] == "always on"

    def test_addRule_creates_environment_if_missing(self):
        flag = _make_flag(environments={})
        flag.addRule({"environment": "production", "logic": {}, "value": "v"})
        assert "production" in flag.environments
        assert len(flag.environments["production"]["rules"]) == 1

    def test_addRule_requires_environment_key(self):
        flag = _make_flag()
        with pytest.raises(ValueError, match="environment"):
            flag.addRule({"logic": {}, "value": True})

    def test_addRule_chaining(self):
        flag = _make_flag(environments={})
        flag.addRule({"environment": "staging", "logic": {}, "value": 1}).addRule(
            {"environment": "staging", "logic": {}, "value": 2}
        )
        assert len(flag.environments["staging"]["rules"]) == 2

    # ------------------------------------------------------------------
    # setEnvironmentEnabled
    # ------------------------------------------------------------------

    def test_setEnvironmentEnabled_existing(self):
        flag = _make_flag(environments={"staging": {"enabled": True, "rules": []}})
        flag.setEnvironmentEnabled("staging", False)
        assert flag.environments["staging"]["enabled"] is False

    def test_setEnvironmentEnabled_new_environment(self):
        flag = _make_flag(environments={})
        flag.setEnvironmentEnabled("production", True)
        assert flag.environments["production"]["enabled"] is True

    # ------------------------------------------------------------------
    # setEnvironmentDefault
    # ------------------------------------------------------------------

    def test_setEnvironmentDefault_existing(self):
        flag = _make_flag(environments={"staging": {"enabled": True}})
        flag.setEnvironmentDefault("staging", "new-default")
        assert flag.environments["staging"]["default"] == "new-default"

    def test_setEnvironmentDefault_new_environment(self):
        flag = _make_flag(environments={})
        flag.setEnvironmentDefault("production", 42)
        assert flag.environments["production"]["default"] == 42

    # ------------------------------------------------------------------
    # clearRules
    # ------------------------------------------------------------------

    def test_clearRules_existing(self):
        flag = _make_flag(environments={"staging": {"enabled": True, "rules": [{"logic": {}, "value": True}]}})
        flag.clearRules("staging")
        assert flag.environments["staging"]["rules"] == []

    def test_clearRules_new_environment(self):
        flag = _make_flag(environments={})
        flag.clearRules("production")
        assert flag.environments["production"]["rules"] == []

    # ------------------------------------------------------------------
    # get (runtime evaluation)
    # ------------------------------------------------------------------

    def test_get_delegates_to_client(self):
        client = MagicMock()
        client._evaluate_handle.return_value = True
        flag = Flag(client, key="k", name="n", type="BOOLEAN", default=False)
        result = flag.get()
        client._evaluate_handle.assert_called_once_with("k", False, None)
        assert result is True

    def test_get_with_context(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "matched"
        flag = Flag(client, key="k", name="n", type="STRING", default="off")
        ctx = [MagicMock()]
        result = flag.get(context=ctx)
        client._evaluate_handle.assert_called_once_with("k", "off", ctx)
        assert result == "matched"


# ===========================================================================
# Typed sync flags
# ===========================================================================


class TestBooleanFlag:
    def test_returns_bool(self):
        client = MagicMock()
        client._evaluate_handle.return_value = True
        flag = BooleanFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.get() is True

    def test_returns_default_on_non_bool(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "not a bool"
        flag = BooleanFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.get() is False


class TestStringFlag:
    def test_returns_string(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "blue"
        flag = StringFlag(client, key="color", name="Color", type="STRING", default="red")
        assert flag.get() == "blue"

    def test_returns_default_on_non_string(self):
        client = MagicMock()
        client._evaluate_handle.return_value = 42
        flag = StringFlag(client, key="color", name="Color", type="STRING", default="red")
        assert flag.get() == "red"


class TestNumberFlag:
    def test_returns_int(self):
        client = MagicMock()
        client._evaluate_handle.return_value = 5
        flag = NumberFlag(client, key="retries", name="Retries", type="NUMERIC", default=3)
        assert flag.get() == 5

    def test_returns_float(self):
        client = MagicMock()
        client._evaluate_handle.return_value = 3.14
        flag = NumberFlag(client, key="rate", name="Rate", type="NUMERIC", default=1.0)
        assert flag.get() == 3.14

    def test_rejects_bool(self):
        client = MagicMock()
        client._evaluate_handle.return_value = True
        flag = NumberFlag(client, key="retries", name="Retries", type="NUMERIC", default=3)
        assert flag.get() == 3

    def test_returns_default_on_string(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "not a number"
        flag = NumberFlag(client, key="retries", name="Retries", type="NUMERIC", default=3)
        assert flag.get() == 3


class TestJsonFlag:
    def test_returns_dict(self):
        client = MagicMock()
        client._evaluate_handle.return_value = {"mode": "dark"}
        flag = JsonFlag(client, key="theme", name="Theme", type="JSON", default={"mode": "light"})
        assert flag.get() == {"mode": "dark"}

    def test_returns_default_on_non_dict(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "not a dict"
        flag = JsonFlag(client, key="theme", name="Theme", type="JSON", default={"mode": "light"})
        assert flag.get() == {"mode": "light"}


# ===========================================================================
# AsyncFlag
# ===========================================================================


class TestAsyncFlag:
    def test_properties(self):
        client = MagicMock()
        flag = AsyncFlag(
            client,
            id="af-1",
            key="async-flag",
            name="Async Flag",
            type="BOOLEAN",
            default=True,
            values=[],
            description="async desc",
            environments={"prod": {"enabled": True}},
        )
        assert flag.id == "af-1"
        assert flag.key == "async-flag"
        assert flag.name == "Async Flag"
        assert flag.description == "async desc"

    def test_defaults(self):
        client = MagicMock()
        flag = AsyncFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.id is None
        assert flag.values == []
        assert flag.environments == {}

    def test_repr(self):
        flag = _make_flag(cls=AsyncFlag)
        r = repr(flag)
        assert "AsyncFlag" in r
        assert "test-flag" in r

    # ------------------------------------------------------------------
    # save() — create path (async)
    # ------------------------------------------------------------------

    def test_save_creates_when_id_is_none(self):
        client = AsyncMock()
        flag = AsyncFlag(client, key="new-flag", name="New", type="BOOLEAN", default=False)
        created = AsyncFlag(client, id="new-id", key="new-flag", name="New", type="BOOLEAN", default=False)
        client._create_flag.return_value = created

        async def _run():
            await flag.save()
            assert flag.id == "new-id"

        asyncio.run(_run())

    # ------------------------------------------------------------------
    # save() — update path (async)
    # ------------------------------------------------------------------

    def test_save_updates_when_id_is_set(self):
        client = AsyncMock()
        flag = AsyncFlag(client, id="existing-id", key="flag", name="Old", type="BOOLEAN", default=False)
        updated = AsyncFlag(client, id="existing-id", key="flag", name="Updated", type="BOOLEAN", default=True)
        client._update_flag.return_value = updated

        async def _run():
            await flag.save()
            assert flag.name == "Updated"
            assert flag.default is True

        asyncio.run(_run())

    # ------------------------------------------------------------------
    # _apply
    # ------------------------------------------------------------------

    def test_apply_copies_all_fields(self):
        client = MagicMock()
        flag = AsyncFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        other = AsyncFlag(
            client,
            id="new-id",
            key="new-key",
            name="new-name",
            type="STRING",
            default="hello",
            values=[{"name": "v", "value": "v"}],
            description="desc",
            environments={"prod": {"enabled": True}},
            created_at="2024-01-01",
            updated_at="2024-06-01",
        )
        flag._apply(other)
        assert flag.id == "new-id"
        assert flag.key == "new-key"
        assert flag.type == "STRING"
        assert flag.default == "hello"

    # ------------------------------------------------------------------
    # addRule — local mutation (sync)
    # ------------------------------------------------------------------

    def test_addRule_appends_to_environment(self):
        flag = _make_flag(cls=AsyncFlag, environments={"staging": {"enabled": True, "rules": []}})
        result = flag.addRule({"environment": "staging", "logic": {"==": [1, 1]}, "value": True})
        assert result is flag
        assert len(flag.environments["staging"]["rules"]) == 1
        assert "environment" not in flag.environments["staging"]["rules"][0]

    def test_addRule_creates_environment_if_missing(self):
        flag = _make_flag(cls=AsyncFlag, environments={})
        flag.addRule({"environment": "production", "logic": {}, "value": "v"})
        assert "production" in flag.environments

    def test_addRule_requires_environment_key(self):
        flag = _make_flag(cls=AsyncFlag)
        with pytest.raises(ValueError, match="environment"):
            flag.addRule({"logic": {}, "value": True})

    # ------------------------------------------------------------------
    # setEnvironmentEnabled / setEnvironmentDefault / clearRules
    # ------------------------------------------------------------------

    def test_setEnvironmentEnabled(self):
        flag = _make_flag(cls=AsyncFlag, environments={})
        flag.setEnvironmentEnabled("staging", True)
        assert flag.environments["staging"]["enabled"] is True

    def test_setEnvironmentDefault(self):
        flag = _make_flag(cls=AsyncFlag, environments={})
        flag.setEnvironmentDefault("staging", "default-val")
        assert flag.environments["staging"]["default"] == "default-val"

    def test_clearRules(self):
        flag = _make_flag(
            cls=AsyncFlag,
            environments={"staging": {"rules": [{"logic": {}, "value": True}]}},
        )
        flag.clearRules("staging")
        assert flag.environments["staging"]["rules"] == []

    # ------------------------------------------------------------------
    # get (runtime evaluation — sync)
    # ------------------------------------------------------------------

    def test_get_delegates_to_client(self):
        client = MagicMock()
        client._evaluate_handle.return_value = True
        flag = AsyncFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.get() is True
        client._evaluate_handle.assert_called_once_with("k", False, None)

    def test_get_with_context(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "val"
        flag = AsyncFlag(client, key="k", name="n", type="STRING", default="off")
        ctx = [MagicMock()]
        assert flag.get(context=ctx) == "val"


# ===========================================================================
# Typed async flags
# ===========================================================================


class TestAsyncBooleanFlag:
    def test_returns_bool(self):
        client = MagicMock()
        client._evaluate_handle.return_value = True
        flag = AsyncBooleanFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.get() is True

    def test_returns_default_on_non_bool(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "not a bool"
        flag = AsyncBooleanFlag(client, key="k", name="n", type="BOOLEAN", default=False)
        assert flag.get() is False


class TestAsyncStringFlag:
    def test_returns_string(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "blue"
        flag = AsyncStringFlag(client, key="color", name="Color", type="STRING", default="red")
        assert flag.get() == "blue"

    def test_returns_default_on_non_string(self):
        client = MagicMock()
        client._evaluate_handle.return_value = 42
        flag = AsyncStringFlag(client, key="color", name="Color", type="STRING", default="red")
        assert flag.get() == "red"


class TestAsyncNumberFlag:
    def test_returns_int(self):
        client = MagicMock()
        client._evaluate_handle.return_value = 5
        flag = AsyncNumberFlag(client, key="retries", name="Retries", type="NUMERIC", default=3)
        assert flag.get() == 5

    def test_returns_float(self):
        client = MagicMock()
        client._evaluate_handle.return_value = 3.14
        flag = AsyncNumberFlag(client, key="rate", name="Rate", type="NUMERIC", default=1.0)
        assert flag.get() == 3.14

    def test_rejects_bool(self):
        client = MagicMock()
        client._evaluate_handle.return_value = True
        flag = AsyncNumberFlag(client, key="retries", name="Retries", type="NUMERIC", default=3)
        assert flag.get() == 3

    def test_returns_default_on_string(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "nope"
        flag = AsyncNumberFlag(client, key="retries", name="Retries", type="NUMERIC", default=3)
        assert flag.get() == 3


class TestAsyncJsonFlag:
    def test_returns_dict(self):
        client = MagicMock()
        client._evaluate_handle.return_value = {"mode": "dark"}
        flag = AsyncJsonFlag(client, key="theme", name="Theme", type="JSON", default={"mode": "light"})
        assert flag.get() == {"mode": "dark"}

    def test_returns_default_on_non_dict(self):
        client = MagicMock()
        client._evaluate_handle.return_value = "not a dict"
        flag = AsyncJsonFlag(client, key="theme", name="Theme", type="JSON", default={"mode": "light"})
        assert flag.get() == {"mode": "light"}
