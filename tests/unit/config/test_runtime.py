"""Tests for ConfigRuntime, ConfigChangeEvent, and ConfigStats."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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

    def test_refresh_with_sync_fetch(self):
        chain = [
            {
                "id": "cfg-1",
                "values": {"retries": 5},
                "environments": {"production": {"values": {"retries": 10}}},
            }
        ]
        new_chain = [
            {
                "id": "cfg-1",
                "values": {"retries": 99},
                "environments": {"production": {"values": {"retries": 99}}},
            }
        ]
        rt = _make_runtime(chain=chain, fetch_chain_fn=lambda: new_chain)
        asyncio.run(rt.refresh())
        assert rt.get("retries") == 99
        assert rt.stats().fetch_count == 2  # 1 initial + 1 refresh

    def test_refresh_with_coroutine_fetch(self):
        chain = [
            {
                "id": "cfg-1",
                "values": {"retries": 5},
                "environments": {"production": {"values": {"retries": 10}}},
            }
        ]
        new_chain = [
            {
                "id": "cfg-1",
                "values": {"retries": 77},
                "environments": {"production": {"values": {"retries": 77}}},
            }
        ]

        async def async_fetch():
            return new_chain

        rt = _make_runtime(chain=chain, fetch_chain_fn=async_fetch)
        asyncio.run(rt.refresh())
        assert rt.get("retries") == 77

    def test_refresh_no_fetch_fn(self):
        rt = _make_runtime()
        # Should not raise when fetch_chain_fn is None
        asyncio.run(rt.refresh())

    def test_refresh_fires_listeners(self):
        chain = [
            {
                "id": "cfg-1",
                "values": {"retries": 5},
                "environments": {"production": {"values": {"retries": 10}}},
            }
        ]
        new_chain = [
            {
                "id": "cfg-1",
                "values": {"retries": 20},
                "environments": {"production": {"values": {"retries": 20}}},
            }
        ]
        rt = _make_runtime(chain=chain, fetch_chain_fn=lambda: new_chain)
        events = []
        rt.on_change(lambda e: events.append(e))
        asyncio.run(rt.refresh())
        assert len(events) == 1
        assert events[0].key == "retries"
        assert events[0].source == "manual"

    def test_get_after_deleted_warns(self):
        rt = _make_runtime()
        rt._deleted = True
        # First access after deletion should not raise but should mark warned
        val = rt.get("retries")
        assert val == 10
        assert rt._access_after_delete_warned is True

    def test_close_with_no_ws(self):
        """Close should work cleanly when no WebSocket is active."""
        rt = _make_runtime()
        rt._ws = None
        rt._ws_loop = None
        asyncio.run(rt.close())
        assert rt._closed is True
        assert rt.connection_status() == "disconnected"

    def test_sync_exit_with_ws_loop(self):
        """Sync __exit__ should close WebSocket via the background loop."""
        rt = _make_runtime()
        mock_ws = MagicMock()
        mock_ws.close = AsyncMock()
        rt._ws = mock_ws
        # Create and start a loop on a background thread
        import threading

        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, daemon=True)
        thread.start()
        rt._ws_loop = loop
        rt._ws_thread = thread
        try:
            rt.__exit__(None, None, None)
        finally:
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=2)
            loop.close()
        assert rt._closed is True


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
