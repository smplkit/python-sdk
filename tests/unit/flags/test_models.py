"""Tests for Flag and AsyncFlag resource models."""

import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from smplkit.flags.models import AsyncFlag, ContextType, Flag


class TestFlag:
    def _make_flag(self, **overrides):
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
        client = MagicMock()
        return Flag(client, **defaults)

    def test_properties(self):
        flag = self._make_flag()
        assert flag.id == "flag-id-1"
        assert flag.key == "test-flag"
        assert flag.name == "Test Flag"
        assert flag.type == "BOOLEAN"
        assert flag.default is False
        assert flag.description == "A test flag"

    def test_repr(self):
        flag = self._make_flag()
        assert "test-flag" in repr(flag)

    def test_update_calls_client(self):
        client = MagicMock()
        flag = Flag(
            client,
            id="id-1",
            key="k",
            name="n",
            type="BOOLEAN",
            default=False,
            values=[],
        )
        updated = Flag(
            client,
            id="id-1",
            key="k",
            name="Updated",
            type="BOOLEAN",
            default=True,
            values=[],
        )
        client._update_flag.return_value = updated
        flag.update(name="Updated", default=True)
        assert flag.name == "Updated"
        assert flag.default is True

    def test_addRule_requires_environment(self):
        flag = self._make_flag()
        with pytest.raises(ValueError, match="environment"):
            flag.addRule({"logic": {}, "value": True})

    def test_addRule_calls_client(self):
        client = MagicMock()
        flag = Flag(
            client,
            id="id-1",
            key="k",
            name="n",
            type="BOOLEAN",
            default=False,
            values=[],
            environments={"staging": {"enabled": True, "rules": []}},
        )
        # get returns a copy of the flag
        client.get.return_value = flag
        updated = Flag(
            client,
            id="id-1",
            key="k",
            name="n",
            type="BOOLEAN",
            default=False,
            values=[],
            environments={"staging": {"enabled": True, "rules": [{"logic": {}, "value": True}]}},
        )
        client._update_flag.return_value = updated
        flag.addRule({"environment": "staging", "logic": {}, "value": True})
        assert client._update_flag.called

    def test_environments_default_empty(self):
        client = MagicMock()
        flag = Flag(client, id="id-1", key="k", name="n", type="BOOLEAN", default=False, values=[])
        assert flag.environments == {}


class TestAsyncFlag:
    def _make_flag(self, **overrides):
        defaults = {
            "id": "flag-id-1",
            "key": "test-flag",
            "name": "Test Flag",
            "type": "BOOLEAN",
            "default": False,
            "values": [{"name": "True", "value": True}],
        }
        defaults.update(overrides)
        client = MagicMock()
        return AsyncFlag(client, **defaults)

    def test_repr(self):
        flag = self._make_flag()
        assert "test-flag" in repr(flag)

    def test_update_calls_client(self):
        client = AsyncMock()
        flag = AsyncFlag(
            client,
            id="id-1",
            key="k",
            name="n",
            type="BOOLEAN",
            default=False,
            values=[],
        )
        updated = AsyncFlag(
            client,
            id="id-1",
            key="k",
            name="Updated",
            type="BOOLEAN",
            default=True,
            values=[],
        )
        client._update_flag.return_value = updated

        async def _run():
            await flag.update(name="Updated", default=True)
            assert flag.name == "Updated"

        asyncio.run(_run())

    def test_addRule_requires_environment(self):
        flag = self._make_flag()

        async def _run():
            with pytest.raises(ValueError, match="environment"):
                await flag.addRule({"logic": {}, "value": True})

        asyncio.run(_run())

    def test_addRule_calls_client(self):
        client = AsyncMock()
        flag = AsyncFlag(
            client,
            id="id-1",
            key="k",
            name="n",
            type="BOOLEAN",
            default=False,
            values=[],
            environments={"staging": {"enabled": True, "rules": []}},
        )
        client.get.return_value = flag
        updated = AsyncFlag(
            client,
            id="id-1",
            key="k",
            name="n",
            type="BOOLEAN",
            default=False,
            values=[],
            environments={"staging": {"enabled": True, "rules": [{"logic": {}, "value": True}]}},
        )
        client._update_flag.return_value = updated

        async def _run():
            await flag.addRule({"environment": "staging", "logic": {}, "value": True})
            assert client._update_flag.called

        asyncio.run(_run())


class TestContextType:
    def test_properties(self):
        ct = ContextType(id="ct-1", key="user", name="User", attributes={"plan": {}})
        assert ct.id == "ct-1"
        assert ct.key == "user"
        assert ct.name == "User"
        assert ct.attributes == {"plan": {}}

    def test_default_attributes(self):
        ct = ContextType(id="ct-1", key="user", name="User")
        assert ct.attributes == {}

    def test_repr(self):
        ct = ContextType(id="ct-1", key="user", name="User")
        assert "user" in repr(ct)
