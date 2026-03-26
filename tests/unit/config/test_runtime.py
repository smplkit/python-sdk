"""Tests for ConfigRuntime, ConfigChangeEvent, and ConfigStats."""

import asyncio
from unittest.mock import patch

from smplkit.config.runtime import ConfigChangeEvent, ConfigRuntime, ConfigStats


def _make_runtime(
    *,
    config_key: str = "test_config",
    config_id: str = "5a0c6be1-0000-0000-0000-000000000001",
    environment: str = "production",
    chain: list | None = None,
    api_key: str = "sk_test",
    base_url: str = "https://config.smplkit.com",
    fetch_chain_fn=None,
) -> ConfigRuntime:
    """Helper to create a ConfigRuntime with sensible defaults.

    Patches the WebSocket thread so it doesn't actually connect.
    """
    if chain is None:
        chain = [
            {
                "id": config_id,
                "values": {"retries": 5, "name": "test", "enabled": True, "count": 42},
                "environments": {
                    "production": {"values": {"retries": 10}},
                },
            }
        ]
    with patch.object(ConfigRuntime, "_start_ws_thread"):
        rt = ConfigRuntime(
            config_key=config_key,
            config_id=config_id,
            environment=environment,
            chain=chain,
            api_key=api_key,
            base_url=base_url,
            fetch_chain_fn=fetch_chain_fn,
        )
    return rt


class TestConfigRuntime:
    def test_get_existing_key(self):
        rt = _make_runtime()
        assert rt.get("retries") == 10

    def test_get_missing_key_returns_none(self):
        rt = _make_runtime()
        assert rt.get("nonexistent") is None

    def test_get_missing_key_with_default(self):
        rt = _make_runtime()
        assert rt.get("nonexistent", default="fallback") == "fallback"

    def test_get_str_returns_string(self):
        rt = _make_runtime()
        assert rt.get_str("name") == "test"

    def test_get_str_returns_default_for_non_string(self):
        rt = _make_runtime()
        assert rt.get_str("retries", default="nope") == "nope"

    def test_get_str_returns_default_for_missing(self):
        rt = _make_runtime()
        assert rt.get_str("missing") is None

    def test_get_int_returns_int(self):
        rt = _make_runtime()
        assert rt.get_int("count") == 42

    def test_get_int_returns_default_for_non_int(self):
        rt = _make_runtime()
        assert rt.get_int("name", default=0) == 0

    def test_get_int_returns_default_for_bool(self):
        """bools are ints in Python, but get_int should not return them."""
        rt = _make_runtime()
        assert rt.get_int("enabled", default=-1) == -1

    def test_get_bool_returns_bool(self):
        rt = _make_runtime()
        assert rt.get_bool("enabled") is True

    def test_get_bool_returns_default_for_non_bool(self):
        rt = _make_runtime()
        assert rt.get_bool("retries", default=False) is False

    def test_get_bool_returns_default_for_missing(self):
        rt = _make_runtime()
        assert rt.get_bool("missing") is None

    def test_get_all_returns_copy(self):
        rt = _make_runtime()
        all_values = rt.get_all()
        assert "retries" in all_values
        # Modifying the copy should not affect the runtime
        all_values["retries"] = 999
        assert rt.get("retries") == 10

    def test_exists_true(self):
        rt = _make_runtime()
        assert rt.exists("retries") is True

    def test_exists_false(self):
        rt = _make_runtime()
        assert rt.exists("ghost") is False

    def test_stats(self):
        rt = _make_runtime()
        stats = rt.stats()
        assert stats.fetch_count == 1
        assert stats.last_fetch_at is not None

    def test_stats_fetch_count_matches_chain_length(self):
        chain = [
            {"id": "a", "values": {"a": 1}, "environments": {}},
            {"id": "b", "values": {"b": 2}, "environments": {}},
            {"id": "c", "values": {"c": 3}, "environments": {}},
        ]
        rt = _make_runtime(chain=chain)
        assert rt.stats().fetch_count == 3

    def test_connection_status_disconnected(self):
        rt = _make_runtime()
        assert rt.connection_status() == "disconnected"

    def test_on_change_registers_listener(self):
        rt = _make_runtime()
        callbacks = []
        rt.on_change(lambda e: callbacks.append(e))
        assert len(rt._listeners) == 1
        assert rt._listeners[0][1] is None  # no key filter

    def test_on_change_with_key_filter(self):
        rt = _make_runtime()
        rt.on_change(lambda e: None, key="retries")
        assert rt._listeners[0][1] == "retries"

    def test_close_sets_closed(self):
        rt = _make_runtime()
        asyncio.run(rt.close())
        assert rt._closed is True
        assert rt.connection_status() == "disconnected"

    def test_sync_context_manager(self):
        rt = _make_runtime()
        with rt as r:
            assert r.get("retries") == 10
        assert rt._closed is True

    def test_async_context_manager(self):
        async def _run():
            rt = _make_runtime()
            async with rt as r:
                assert r.get("retries") == 10
            assert rt._closed is True

        asyncio.run(_run())

    def test_repr(self):
        rt = _make_runtime()
        r = repr(rt)
        assert "ConfigRuntime" in r
        assert "test_config" in r
        assert "production" in r

    def test_empty_chain(self):
        rt = _make_runtime(chain=[])
        assert rt.get_all() == {}
        assert rt.stats().fetch_count == 0


class TestConfigChangeEvent:
    def test_attributes(self):
        event = ConfigChangeEvent(
            key="retries", old_value=3, new_value=5, source="websocket"
        )
        assert event.key == "retries"
        assert event.old_value == 3
        assert event.new_value == 5
        assert event.source == "websocket"

    def test_repr(self):
        event = ConfigChangeEvent(
            key="retries", old_value=3, new_value=5, source="websocket"
        )
        r = repr(event)
        assert "ConfigChangeEvent" in r
        assert "retries" in r


class TestConfigStats:
    def test_attributes(self):
        stats = ConfigStats(fetch_count=2, last_fetch_at="2026-01-01T00:00:00Z")
        assert stats.fetch_count == 2
        assert stats.last_fetch_at == "2026-01-01T00:00:00Z"

    def test_repr(self):
        stats = ConfigStats(fetch_count=2, last_fetch_at=None)
        r = repr(stats)
        assert "ConfigStats" in r
        assert "2" in r
