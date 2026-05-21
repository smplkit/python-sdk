"""Tests for the SDK-side discovery pipeline:

- ``_ConfigRegistrationBuffer`` (mgmt buffer)
- ``ConfigClient.get_or_create`` + typed getters on ``LiveConfigProxy``
- Pydantic introspection helpers
- Pre-start flush hook
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import NotFoundError
from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.config.client import (
    LiveConfigProxy,
    _is_pydantic_model,
    _iter_pydantic_items,
    _pydantic_field_type,
)
from smplkit.management._buffer import _ConfigRegistrationBuffer
from smplkit.management.client import _build_config_bulk_request


# ===========================================================================
# _ConfigRegistrationBuffer
# ===========================================================================


class TestConfigRegistrationBuffer:
    def test_declare_then_drain(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="svc", environment="prod")
        batch = buf.drain()
        assert len(batch) == 1
        assert batch[0]["id"] == "billing"
        assert batch[0]["items"] == {}
        assert batch[0]["service"] == "svc"
        assert batch[0]["environment"] == "prod"

    def test_declare_includes_optional_metadata(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare(
            "billing",
            service="s",
            environment="e",
            parent="common",
            name="Billing",
            description="Plan limits.",
        )
        entry = buf.drain()[0]
        assert entry["parent"] == "common"
        assert entry["name"] == "Billing"
        assert entry["description"] == "Plan limits."

    def test_declare_omits_none_metadata(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service=None, environment=None)
        entry = buf.drain()[0]
        # service/environment None → field not included in payload.
        assert "service" not in entry
        assert "environment" not in entry
        assert "parent" not in entry
        assert "name" not in entry
        assert "description" not in entry

    def test_declare_is_idempotent(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="s1", environment="e1")
        buf.declare("billing", service="s2", environment="e2")  # ignored
        entries = buf.drain()
        assert len(entries) == 1
        assert entries[0]["service"] == "s1"  # first writer wins

    def test_add_item_attaches_to_existing_entry(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="s", environment="e")
        buf.add_item("billing", "max_seats", "NUMBER", 5, "Max seats.")
        entry = buf.drain()[0]
        assert entry["items"] == {
            "max_seats": {
                "value": 5,
                "type": "NUMBER",
                "description": "Max seats.",
            }
        }

    def test_add_item_without_description_omits_field(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="s", environment="e")
        buf.add_item("billing", "k", "STRING", "foo")
        entry = buf.drain()[0]
        assert entry["items"]["k"] == {"value": "foo", "type": "STRING"}

    def test_add_item_without_declare_is_dropped(self):
        buf = _ConfigRegistrationBuffer()
        buf.add_item("unknown", "k", "NUMBER", 1)
        assert buf.drain() == []

    def test_add_item_dedups_within_session(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="s", environment="e")
        buf.add_item("billing", "max_seats", "NUMBER", 5)
        buf.add_item("billing", "max_seats", "NUMBER", 99)  # ignored — already pending
        entry = buf.drain()[0]
        assert entry["items"]["max_seats"]["value"] == 5

    def test_add_item_dedups_across_drains(self):
        """After a successful flush (drain), the same item must not re-send."""
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="s", environment="e")
        buf.add_item("billing", "max_seats", "NUMBER", 5)
        first = buf.drain()
        assert first[0]["items"]
        buf.add_item("billing", "max_seats", "NUMBER", 5)  # already sent
        assert buf.drain() == []

    def test_delta_after_drain_includes_metadata(self):
        """A new item declared after drain creates a fresh pending entry."""
        buf = _ConfigRegistrationBuffer()
        buf.declare(
            "billing",
            service="svc",
            environment="prod",
            parent="common",
        )
        buf.add_item("billing", "k1", "NUMBER", 1)
        buf.drain()

        buf.add_item("billing", "k2", "NUMBER", 2)
        delta = buf.drain()
        assert len(delta) == 1
        # Stored metadata is reattached so the server can attribute the source.
        assert delta[0]["service"] == "svc"
        assert delta[0]["environment"] == "prod"
        assert delta[0]["parent"] == "common"
        assert delta[0]["items"] == {"k2": {"value": 2, "type": "NUMBER"}}

    def test_drain_clears_pending(self):
        buf = _ConfigRegistrationBuffer()
        buf.declare("billing", service="s", environment="e")
        assert buf.drain() != []
        assert buf.drain() == []

    def test_pending_count(self):
        buf = _ConfigRegistrationBuffer()
        assert buf.pending_count == 0
        buf.declare("billing", service="s", environment="e")
        assert buf.pending_count == 1
        buf.declare("user-service", service="s", environment="e")
        assert buf.pending_count == 2
        buf.drain()
        assert buf.pending_count == 0


# ===========================================================================
# _build_config_bulk_request helper
# ===========================================================================


class TestBuildConfigBulkRequest:
    def test_empty_returns_none(self):
        assert _build_config_bulk_request([]) is None

    def test_translates_entry(self):
        body = _build_config_bulk_request(
            [
                {
                    "id": "billing",
                    "items": {
                        "max_seats": {"value": 5, "type": "NUMBER", "description": "Max."},
                    },
                    "service": "svc",
                    "environment": "prod",
                    "parent": "common",
                    "name": "Billing",
                    "description": "Plan limits.",
                }
            ]
        )
        assert body is not None
        assert len(body.configs) == 1
        item = body.configs[0]
        assert item.id == "billing"
        assert item.name == "Billing"
        assert item.parent == "common"
        assert "max_seats" in item.items.additional_properties

    def test_omits_unset_fields(self):
        body = _build_config_bulk_request([{"id": "minimal", "items": {}}])
        item = body.configs[0]
        # No items, no metadata — generator UNSET sentinels remain.
        assert item.id == "minimal"

    def test_translates_multiple_entries(self):
        body = _build_config_bulk_request(
            [
                {"id": "a", "items": {}},
                {"id": "b", "items": {}},
            ]
        )
        assert [c.id for c in body.configs] == ["a", "b"]


# ===========================================================================
# Pydantic introspection helpers
# ===========================================================================


class TestPydanticHelpers:
    def test_field_type_mapping(self):
        assert _pydantic_field_type(bool) == "BOOLEAN"
        assert _pydantic_field_type(int) == "NUMBER"
        assert _pydantic_field_type(float) == "NUMBER"
        assert _pydantic_field_type(str) == "STRING"
        # Anything else → JSON escape hatch.
        assert _pydantic_field_type(dict) == "JSON"
        assert _pydantic_field_type(list) == "JSON"
        assert _pydantic_field_type(object) == "JSON"

    def test_is_pydantic_model_negative(self):
        assert not _is_pydantic_model(int)
        assert not _is_pydantic_model("not a class")
        assert not _is_pydantic_model(None)

    def test_iter_items_flat_fields(self):
        from pydantic import BaseModel, Field

        class Billing(BaseModel):
            max_seats: int = 5
            trial_days: int = Field(default=14, description="Trial.")
            enabled: bool = True
            name: str = "default"

        items = _iter_pydantic_items(Billing)
        # Order matches declaration order.
        assert [(k, t) for (k, t, _, _) in items] == [
            ("max_seats", "NUMBER"),
            ("trial_days", "NUMBER"),
            ("enabled", "BOOLEAN"),
            ("name", "STRING"),
        ]
        # Description propagates when present.
        trial = next(i for i in items if i[0] == "trial_days")
        assert trial[3] == "Trial."
        # And is None when absent.
        max_seats = next(i for i in items if i[0] == "max_seats")
        assert max_seats[3] is None

    def test_iter_items_flattens_nested_models(self):
        from pydantic import BaseModel

        class Database(BaseModel):
            host: str = "localhost"
            port: int = 5432

        class App(BaseModel):
            database: Database = Database()
            debug: bool = False

        items = _iter_pydantic_items(App)
        keys = [k for (k, _, _, _) in items]
        # Nested keys flatten with dot-notation, recursion is depth-first.
        assert "database.host" in keys
        assert "database.port" in keys
        assert "debug" in keys

    def test_iter_items_skips_fields_with_no_default(self):
        from pydantic import BaseModel

        class Required(BaseModel):
            mandatory: int  # no default
            optional: int = 5

        items = _iter_pydantic_items(Required)
        keys = [k for (k, _, _, _) in items]
        assert "mandatory" not in keys
        assert "optional" in keys

    def test_iter_items_handles_default_factory(self):
        from pydantic import BaseModel, Field

        class WithFactory(BaseModel):
            tags: list = Field(default_factory=list)

        items = _iter_pydantic_items(WithFactory)
        assert items[0] == ("tags", "JSON", [], None)

    def test_iter_items_drops_field_with_failing_factory(self):
        from pydantic import BaseModel, Field

        def bad():
            raise RuntimeError("boom")

        class WithBadFactory(BaseModel):
            tags: list = Field(default_factory=bad)
            ok: int = 5

        items = _iter_pydantic_items(WithBadFactory)
        keys = [k for (k, _, _, _) in items]
        assert "tags" not in keys
        assert "ok" in keys

    def test_iter_items_returns_empty_for_non_pydantic(self):
        class Plain:
            pass

        assert _iter_pydantic_items(Plain) == []


# ===========================================================================
# ConfigClient.get_or_create + typed getters (sync)
# ===========================================================================


def _new_sync_client() -> SmplClient:
    return SmplClient(api_key="sk_test", environment="prod", service="svc")


class TestGetOrCreateSync:
    def test_returns_same_proxy_instance_on_repeat_calls(self):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {}}
        with patch.object(client.manage.config, "register_config") as register:
            with patch.object(client.config, "start"):
                p1 = client.config.get_or_create("billing")
                p2 = client.config.get_or_create("billing")
        assert p1 is p2
        # register_config still called twice (idempotent at buffer level).
        assert register.call_count == 2

    def test_registers_config_metadata(self):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {}}
        with patch.object(client.manage.config, "register_config") as register:
            with patch.object(client.config, "start"):
                client.config.get_or_create("billing", parent="common", name="Billing", description="d")
        register.assert_called_once_with(
            "billing",
            service="svc",
            environment="prod",
            parent="common",
            name="Billing",
            description="d",
        )

    def test_parent_handle_resolves_to_id(self):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"common": {}, "premium": {}}
        with patch.object(client.config, "start"):
            common = client.config.get_or_create("common")
            with patch.object(client.manage.config, "register_config") as register:
                client.config.get_or_create("premium", parent=common)
        register.assert_called_once()
        kwargs = register.call_args.kwargs
        assert kwargs["parent"] == "common"

    def test_get_returns_same_cached_proxy(self):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {"k": 1}}
        p1 = client.config.get("billing")
        p2 = client.config.get("billing")
        assert p1 is p2

    def test_get_raises_not_found_for_missing(self):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {}
        with pytest.raises(NotFoundError):
            client.config.get("missing")

    def test_get_or_create_does_not_raise_for_missing(self):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {}  # config not yet in cache
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("new-config")
        assert isinstance(proxy, LiveConfigProxy)

    def test_pydantic_model_triggers_item_registration(self):
        from pydantic import BaseModel

        class Billing(BaseModel):
            max_seats: int = 5
            tier: str = "free"

        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {}}
        with patch.object(client.manage.config, "register_config_item") as reg_item:
            with patch.object(client.config, "start"):
                client.config.get_or_create("billing", model=Billing)
        keys_registered = [c.args[1] for c in reg_item.call_args_list]
        assert "max_seats" in keys_registered
        assert "tier" in keys_registered

    def test_cached_proxy_upgrades_model_on_subsequent_call(self):
        from pydantic import BaseModel

        class M(BaseModel):
            v: int = 1

        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"x": {}}
        with patch.object(client.config, "start"):
            untyped = client.config.get_or_create("x")
            typed = client.config.get_or_create("x", model=M)
        assert untyped is typed
        # The proxy was upgraded with the model.
        assert object.__getattribute__(typed, "_model") is M


# ===========================================================================
# LiveConfigProxy typed getters
# ===========================================================================


class TestTypedGetters:
    def _client_with_value(self, key: str, value):
        client = _new_sync_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {key: value}}
        return client

    def test_get_bool_returns_value(self):
        client = self._client_with_value("enabled", True)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_bool("enabled", False) is True

    def test_get_bool_returns_default_when_missing(self):
        client = self._client_with_value("other", True)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_bool("enabled", False) is False

    def test_get_bool_returns_default_on_type_mismatch(self, caplog):
        client = self._client_with_value("enabled", "not a bool")
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with caplog.at_level(logging.WARNING, logger="smplkit"):
            assert proxy.get_bool("enabled", False) is False
        assert any("expected BOOLEAN" in r.message for r in caplog.records)

    def test_get_int_returns_value(self):
        client = self._client_with_value("max", 5)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_int("max", 0) == 5

    def test_get_int_rejects_bool(self, caplog):
        """bool is an int subclass; the int getter must reject it explicitly."""
        client = self._client_with_value("max", True)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with caplog.at_level(logging.WARNING, logger="smplkit"):
            assert proxy.get_int("max", 99) == 99
        assert any("expected NUMBER (int), got bool" in r.message for r in caplog.records)

    def test_get_int_returns_default_when_missing(self):
        client = self._client_with_value("other", 5)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_int("max", 99) == 99

    def test_get_int_returns_default_on_type_mismatch(self, caplog):
        client = self._client_with_value("max", "not a number")
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with caplog.at_level(logging.WARNING, logger="smplkit"):
            assert proxy.get_int("max", 99) == 99
        assert any("expected NUMBER (int)" in r.message for r in caplog.records)

    def test_get_float_coerces_int_to_float(self):
        client = self._client_with_value("ratio", 1)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        result = proxy.get_float("ratio", 0.0)
        assert result == 1.0
        assert isinstance(result, float)

    def test_get_float_accepts_float(self):
        client = self._client_with_value("ratio", 0.75)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_float("ratio", 0.0) == 0.75

    def test_get_float_rejects_bool(self, caplog):
        client = self._client_with_value("ratio", True)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with caplog.at_level(logging.WARNING, logger="smplkit"):
            assert proxy.get_float("ratio", 0.0) == 0.0
        assert any("got bool" in r.message for r in caplog.records)

    def test_get_float_returns_default_when_missing(self):
        client = self._client_with_value("other", 1.0)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_float("ratio", 0.5) == 0.5

    def test_get_float_returns_default_on_type_mismatch(self, caplog):
        client = self._client_with_value("ratio", "not a number")
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with caplog.at_level(logging.WARNING, logger="smplkit"):
            assert proxy.get_float("ratio", 0.5) == 0.5
        assert any("expected NUMBER (float)" in r.message for r in caplog.records)

    def test_get_string_returns_value(self):
        client = self._client_with_value("name", "billing")
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_string("name", "") == "billing"

    def test_get_string_returns_default_when_missing(self):
        client = self._client_with_value("other", "x")
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_string("name", "default") == "default"

    def test_get_string_returns_default_on_type_mismatch(self, caplog):
        client = self._client_with_value("name", 42)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with caplog.at_level(logging.WARNING, logger="smplkit"):
            assert proxy.get_string("name", "default") == "default"
        assert any("expected STRING" in r.message for r in caplog.records)

    def test_get_json_returns_arbitrary_value(self):
        client = self._client_with_value("payload", {"nested": [1, 2, 3]})
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_json("payload", {}) == {"nested": [1, 2, 3]}

    def test_get_json_returns_default_when_missing(self):
        client = self._client_with_value("other", "x")
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        assert proxy.get_json("payload", {"fallback": True}) == {"fallback": True}

    def test_typed_getter_registers_item(self):
        client = self._client_with_value("max", 5)
        with patch.object(client.config, "start"):
            proxy = client.config.get_or_create("billing")
        with patch.object(client.manage.config, "register_config_item") as reg:
            proxy.get_int("max", 99, description="The cap.")
        reg.assert_called_once_with("billing", "max", "NUMBER", 99, "The cap.")


# ===========================================================================
# Pre-start flush hook
# ===========================================================================


class TestPreStartFlush:
    def test_sync_start_flushes_buffer_before_fetch(self):
        client = _new_sync_client()
        with patch.object(client.manage.config, "flush") as flush:
            with patch.object(client.config, "_do_refresh"):
                with patch.object(client.config, "_parent") as parent:
                    parent._ensure_ws.return_value = MagicMock()
                    client.config.start()
        assert flush.called

    def test_sync_start_swallows_flush_errors(self, caplog):
        client = _new_sync_client()
        with patch.object(client.manage.config, "flush", side_effect=RuntimeError("boom")):
            with patch.object(client.config, "_do_refresh"):
                with patch.object(client.config, "_parent") as parent:
                    parent._ensure_ws.return_value = MagicMock()
                    with caplog.at_level(logging.WARNING, logger="smplkit"):
                        client.config.start()
        assert any("Pre-start config discovery flush" in r.message for r in caplog.records)


# ===========================================================================
# Async equivalents
# ===========================================================================


def _new_async_client() -> AsyncSmplClient:
    return AsyncSmplClient(api_key="sk_test", environment="prod", service="svc")


class TestAsyncGetOrCreate:
    def test_returns_same_proxy(self):
        client = _new_async_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {}}

        async def _run():
            with patch.object(client.manage.config, "register_config"):
                with patch.object(client.config, "start") as start:

                    async def noop():
                        return None

                    start.return_value = noop()
                    p1 = await client.config.get_or_create("billing")
                with patch.object(client.config, "start") as start:

                    async def noop2():
                        return None

                    start.return_value = noop2()
                    p2 = await client.config.get_or_create("billing")
            assert p1 is p2

        asyncio.run(_run())

    def test_parent_handle_resolves_to_id(self):
        client = _new_async_client()
        client.config._connected = True
        client.config._config_cache = {"common": {}, "premium": {}}

        async def _run():
            with patch.object(client.config, "start") as start:

                async def noop():
                    return None

                start.return_value = noop()
                common = await client.config.get_or_create("common")

            with patch.object(client.manage.config, "register_config") as register:
                with patch.object(client.config, "start") as start:

                    async def noop2():
                        return None

                    start.return_value = noop2()
                    await client.config.get_or_create("premium", parent=common)
            register.assert_called_once()
            assert register.call_args.kwargs["parent"] == "common"

        asyncio.run(_run())

    def test_pydantic_model_triggers_items(self):
        from pydantic import BaseModel

        class Billing(BaseModel):
            seats: int = 5

        client = _new_async_client()
        client.config._connected = True
        client.config._config_cache = {"billing": {}}

        async def _run():
            with patch.object(client.manage.config, "register_config_item") as reg:
                with patch.object(client.config, "start") as start:

                    async def noop():
                        return None

                    start.return_value = noop()
                    await client.config.get_or_create("billing", model=Billing)
            assert any(c.args[1] == "seats" for c in reg.call_args_list)

        asyncio.run(_run())

    def test_get_raises_not_found(self):
        client = _new_async_client()
        client.config._connected = True
        client.config._config_cache = {}

        async def _run():
            with pytest.raises(NotFoundError):
                await client.config.get("missing")

        asyncio.run(_run())

    def test_async_cached_proxy_upgrades_model_on_subsequent_call(self):
        from pydantic import BaseModel

        class M(BaseModel):
            v: int = 1

        client = _new_async_client()
        client.config._connected = True
        client.config._config_cache = {"x": {}}

        async def _run():
            with patch.object(client.config, "start") as start:

                async def noop():
                    return None

                start.return_value = noop()
                untyped = await client.config.get_or_create("x")

            with patch.object(client.config, "start") as start:

                async def noop2():
                    return None

                start.return_value = noop2()
                typed = await client.config.get_or_create("x", model=M)

            assert untyped is typed
            assert object.__getattribute__(typed, "_model") is M

        asyncio.run(_run())

    def test_async_start_flushes_buffer_before_fetch(self):
        client = _new_async_client()

        async def _run():
            async def noop_flush():
                return None

            with patch.object(client.manage.config, "flush", side_effect=noop_flush) as flush:
                with patch.object(client.config, "_do_refresh") as refresh:

                    async def noop_refresh(source):
                        return None

                    refresh.side_effect = noop_refresh
                    with patch.object(client.config, "_parent") as parent:
                        parent._ensure_ws.return_value = MagicMock()
                        await client.config.start()
            assert flush.called

        asyncio.run(_run())

    def test_async_start_swallows_flush_errors(self, caplog):
        client = _new_async_client()

        async def _run():
            async def boom_flush():
                raise RuntimeError("boom")

            with patch.object(client.manage.config, "flush", side_effect=boom_flush):
                with patch.object(client.config, "_do_refresh") as refresh:

                    async def noop_refresh(source):
                        return None

                    refresh.side_effect = noop_refresh
                    with patch.object(client.config, "_parent") as parent:
                        parent._ensure_ws.return_value = MagicMock()
                        with caplog.at_level(logging.WARNING, logger="smplkit"):
                            await client.config.start()
            assert any("Pre-start config discovery flush" in r.message for r in caplog.records)

        asyncio.run(_run())
