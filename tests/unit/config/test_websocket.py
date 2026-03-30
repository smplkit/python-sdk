"""Tests for WebSocket integration in ConfigRuntime."""

import asyncio
import json
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
import websockets.frames

from smplkit.config.runtime import ConfigRuntime, _BACKOFF_SCHEDULE


# ---------------------------------------------------------------------------
# Helper to build a ConfigRuntime without starting the WS thread
# ---------------------------------------------------------------------------

def _make_runtime(
    *,
    config_key: str = "test_config",
    config_id: str = "cfg-001",
    environment: str = "production",
    chain: list | None = None,
    api_key: str = "sk_test",
    base_url: str = "https://config.smplkit.com",
    fetch_chain_fn=None,
    use_items: bool = False,
) -> ConfigRuntime:
    if chain is None:
        if use_items:
            chain = [
                {
                    "id": config_id,
                    "items": {
                        "retries": {"value": 5, "type": "NUMBER"},
                        "name": {"value": "test", "type": "STRING"},
                    },
                    "environments": {
                        "production": {"values": {"retries": 10}},
                    },
                }
            ]
        else:
            chain = [
                {
                    "id": config_id,
                    "values": {"retries": 5, "name": "test"},
                    "environments": {
                        "production": {"values": {"retries": 10}},
                    },
                }
            ]
    with patch.object(ConfigRuntime, "_start_ws_thread"):
        return ConfigRuntime(
            config_key=config_key,
            config_id=config_id,
            environment=environment,
            chain=chain,
            api_key=api_key,
            base_url=base_url,
            fetch_chain_fn=fetch_chain_fn,
        )


# ===================================================================
# 1. Cache update from WebSocket message
# ===================================================================


class TestHandleConfigChanged:
    """Test _handle_config_changed with various change scenarios."""

    def test_key_changed_updates_cache_and_fires_listener(self):
        """config_changed with a key change updates cache and fires listener."""
        rt = _make_runtime()
        assert rt.get("retries") == 10

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "retries", "old_value": 10, "new_value": 7},
            ],
        })

        assert rt.get("retries") == 7
        assert len(events) == 1
        assert events[0].key == "retries"
        assert events[0].old_value == 10
        assert events[0].new_value == 7
        assert events[0].source == "websocket"

    def test_key_added_appears_in_cache(self):
        """config_changed with a new key adds it to the cache."""
        rt = _make_runtime()
        assert rt.get("new_key") is None

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "new_key", "old_value": None, "new_value": "hello"},
            ],
        })

        assert rt.get("new_key") == "hello"
        assert len(events) == 1
        assert events[0].key == "new_key"

    def test_key_removed_absent_from_cache(self):
        """config_changed with a removed key removes it from the cache."""
        rt = _make_runtime()
        assert rt.get("name") == "test"

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "name", "old_value": "test", "new_value": None},
            ],
        })

        assert rt.get("name") is None
        assert len(events) == 1
        assert events[0].old_value == "test"
        assert events[0].new_value is None

    def test_parent_change_reflected_in_resolved_cache(self):
        """config_changed for a parent config updates the child's resolved cache."""
        parent_id = "parent-001"
        child_id = "child-001"
        chain = [
            {
                "id": child_id,
                "values": {"child_key": "child_val"},
                "environments": {},
            },
            {
                "id": parent_id,
                "values": {"inherited_key": "old_parent_val"},
                "environments": {},
            },
        ]
        rt = _make_runtime(config_id=child_id, chain=chain)
        assert rt.get("inherited_key") == "old_parent_val"

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": parent_id,
            "changes": [
                {"key": "inherited_key", "old_value": "old_parent_val", "new_value": "new_parent_val"},
            ],
        })

        assert rt.get("inherited_key") == "new_parent_val"
        assert len(events) == 1
        assert events[0].new_value == "new_parent_val"

    def test_parent_change_overridden_by_child_no_listener_fired(self):
        """If the child overrides the key, a parent change doesn't affect resolved cache."""
        parent_id = "parent-001"
        child_id = "child-001"
        chain = [
            {
                "id": child_id,
                "values": {"shared_key": "child_wins"},
                "environments": {},
            },
            {
                "id": parent_id,
                "values": {"shared_key": "parent_val"},
                "environments": {},
            },
        ]
        rt = _make_runtime(config_id=child_id, chain=chain)
        assert rt.get("shared_key") == "child_wins"

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": parent_id,
            "changes": [
                {"key": "shared_key", "old_value": "parent_val", "new_value": "new_parent_val"},
            ],
        })

        # Child still wins
        assert rt.get("shared_key") == "child_wins"
        # No listener should fire because resolved cache didn't change
        assert len(events) == 0

    def test_key_specific_listener_only_fires_for_matching_key(self):
        """Key-specific listener fires only for its key, not others."""
        rt = _make_runtime()

        retries_events = []
        all_events = []
        rt.on_change(lambda e: retries_events.append(e), key="retries")
        rt.on_change(lambda e: all_events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "name", "old_value": "test", "new_value": "updated"},
            ],
        })

        assert len(retries_events) == 0  # not "retries"
        assert len(all_events) == 1  # global listener fires

    def test_global_listener_fires_for_all_changes(self):
        """Global listener fires for every changed key."""
        rt = _make_runtime()
        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "retries", "old_value": 10, "new_value": 7},
                {"key": "name", "old_value": "test", "new_value": "updated"},
            ],
        })

        assert len(events) == 2
        changed_keys = {e.key for e in events}
        assert changed_keys == {"retries", "name"}

    def test_listener_exception_is_caught_other_listeners_fire(self):
        """A broken listener doesn't prevent other listeners from firing."""
        rt = _make_runtime()

        good_events = []

        def bad_listener(event):
            raise ValueError("boom")

        rt.on_change(bad_listener)
        rt.on_change(lambda e: good_events.append(e))

        # Should not raise
        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "retries", "old_value": 10, "new_value": 7},
            ],
        })

        assert len(good_events) == 1

    def test_unknown_config_id_is_ignored(self):
        """config_changed for an unknown config_id is silently ignored."""
        rt = _make_runtime()
        old_cache = rt.get_all()

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "unknown-id",
            "changes": [
                {"key": "retries", "old_value": 10, "new_value": 999},
            ],
        })

        assert rt.get_all() == old_cache

    def test_empty_changes_is_noop(self):
        """config_changed with empty changes list is a no-op."""
        rt = _make_runtime()
        old_cache = rt.get_all()

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [],
        })

        assert rt.get_all() == old_cache

    def test_key_changed_with_items_format(self):
        """config_changed wraps values in {value: ...} when chain uses items key."""
        rt = _make_runtime(use_items=True)
        assert rt.get("retries") == 10

        rt._handle_config_changed({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [
                {"key": "retries", "old_value": 10, "new_value": 7},
            ],
        })

        assert rt.get("retries") == 7
        # Verify the chain entry stores it wrapped
        chain_entry = rt._chain[0]
        assert chain_entry["items"]["retries"] == {"value": 7}


# ===================================================================
# 2. config_deleted handling
# ===================================================================


class TestHandleConfigDeleted:
    def test_sets_closed_and_deleted(self):
        rt = _make_runtime()
        rt._handle_config_deleted({
            "type": "config_deleted",
            "config_id": "cfg-001",
        })
        assert rt._closed is True
        assert rt._deleted is True
        assert rt.connection_status() == "disconnected"

    def test_get_still_works_after_deletion(self):
        """get() returns stale cache after deletion (graceful degradation)."""
        rt = _make_runtime()
        rt._handle_config_deleted({
            "type": "config_deleted",
            "config_id": "cfg-001",
        })
        # Should still return cached value
        assert rt.get("retries") == 10


# ===================================================================
# 3. Connection status
# ===================================================================


class TestConnectionStatus:
    def test_initial_status_disconnected(self):
        rt = _make_runtime()
        # WS thread is mocked out, so status stays "disconnected"
        assert rt.connection_status() == "disconnected"

    def test_status_after_close(self):
        rt = _make_runtime()
        asyncio.run(rt.close())
        assert rt.connection_status() == "disconnected"


# ===================================================================
# 4. Reconnection
# ===================================================================


class TestReconnection:
    def test_backoff_schedule(self):
        assert _BACKOFF_SCHEDULE == [1, 2, 4, 8, 16, 32, 60]

    def test_resync_cache_calls_fetch_chain_fn(self):
        """_resync_cache fetches the chain and re-resolves."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 99},
                "environments": {"production": {"values": {}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)

        old_count = rt.stats().fetch_count
        asyncio.run(rt._resync_cache())

        mock_fetch.assert_called_once()
        assert rt.get("retries") == 99
        assert rt.stats().fetch_count == old_count + 1

    def test_resync_fires_listeners_for_changes(self):
        """_resync_cache fires listeners for changes detected during resync."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 99, "name": "test"},
                "environments": {"production": {"values": {}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)

        events = []
        rt.on_change(lambda e: events.append(e))

        asyncio.run(rt._resync_cache())

        assert len(events) == 1
        assert events[0].key == "retries"
        assert events[0].source == "websocket"

    def test_resync_without_fetch_fn_is_noop(self):
        rt = _make_runtime(fetch_chain_fn=None)
        # Should not raise
        asyncio.run(rt._resync_cache())


# ===================================================================
# 5. Manual refresh
# ===================================================================


class TestManualRefresh:
    def test_refresh_fetches_and_resolves(self):
        """refresh() fetches chain, re-resolves, and updates cache."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 42},
                "environments": {"production": {"values": {}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)
        old_count = rt.stats().fetch_count

        asyncio.run(rt.refresh())

        mock_fetch.assert_called_once()
        assert rt.get("retries") == 42
        assert rt.stats().fetch_count == old_count + 1

    def test_refresh_fires_listeners_with_manual_source(self):
        """refresh() fires listeners with source='manual'."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 42, "name": "test"},
                "environments": {"production": {"values": {}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)

        events = []
        rt.on_change(lambda e: events.append(e))

        asyncio.run(rt.refresh())

        assert len(events) == 1
        assert events[0].source == "manual"
        assert events[0].key == "retries"

    def test_refresh_no_change_no_listener(self):
        """refresh() with no cache changes fires no listeners."""
        # Return same chain as initial
        chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 5, "name": "test"},
                "environments": {"production": {"values": {"retries": 10}}},
            }
        ]
        mock_fetch = MagicMock(return_value=chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)

        events = []
        rt.on_change(lambda e: events.append(e))

        asyncio.run(rt.refresh())

        assert len(events) == 0

    def test_refresh_without_fetch_fn_is_noop(self):
        rt = _make_runtime(fetch_chain_fn=None)
        # Should not raise
        asyncio.run(rt.refresh())


# ===================================================================
# 6. Thread safety
# ===================================================================


class TestThreadSafety:
    def test_concurrent_gets_while_cache_updates(self):
        """Concurrent get() calls while cache is being updated don't raise."""
        rt = _make_runtime()

        errors = []
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                try:
                    rt.get("retries")
                    rt.get_all()
                    rt.exists("retries")
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        for t in threads:
            t.start()

        # Perform cache updates
        for i in range(50):
            rt._handle_config_changed({
                "type": "config_changed",
                "config_id": "cfg-001",
                "changes": [
                    {"key": "retries", "old_value": None, "new_value": i},
                ],
            })

        stop.set()
        for t in threads:
            t.join(timeout=2.0)

        assert errors == []


# ===================================================================
# 7. WebSocket URL building
# ===================================================================


class TestBuildWsUrl:
    def test_https_to_wss(self):
        rt = _make_runtime(base_url="https://config.smplkit.com", api_key="sk_test_key")
        url = rt._build_ws_url()
        assert url == "wss://config.smplkit.com/api/ws/v1/configs?api_key=sk_test_key"

    def test_http_to_ws(self):
        rt = _make_runtime(base_url="http://localhost:8080", api_key="sk_dev")
        url = rt._build_ws_url()
        assert url == "ws://localhost:8080/api/ws/v1/configs?api_key=sk_dev"

    def test_trailing_slash_stripped(self):
        rt = _make_runtime(base_url="https://config.smplkit.com/", api_key="sk_test")
        url = rt._build_ws_url()
        assert url == "wss://config.smplkit.com/api/ws/v1/configs?api_key=sk_test"


# ===================================================================
# 8. WebSocket connect/subscribe flow
# ===================================================================


class TestWsConnectAndSubscribe:
    def test_connect_sends_subscribe_and_enters_loop(self):
        """_connect_and_subscribe opens WS, sends subscribe, reads confirmation."""
        rt = _make_runtime()

        mock_ws = AsyncMock()
        subscribe_confirm = json.dumps({
            "type": "subscribed",
            "config_id": "cfg-001",
            "environment": "production",
        })

        # recv() returns confirmation first, then we break by being closed
        mock_ws.recv = AsyncMock(return_value=subscribe_confirm)
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        async def _run():
            with patch("smplkit.config.runtime.websockets.asyncio.client.connect",
                        new_callable=AsyncMock, return_value=mock_ws):
                # Close immediately to exit receive loop
                rt._closed = True
                await rt._connect_and_subscribe()

        asyncio.run(_run())
        assert rt._connection_status == "connected"

    def test_connect_error_response_raises(self):
        """_connect_and_subscribe raises on error response."""
        rt = _make_runtime()

        mock_ws = AsyncMock()
        error_response = json.dumps({
            "type": "error",
            "message": "Config not found or access denied.",
        })

        mock_ws.recv = AsyncMock(return_value=error_response)
        mock_ws.send = AsyncMock()

        async def _run():
            with patch("smplkit.config.runtime.websockets.asyncio.client.connect",
                        new_callable=AsyncMock, return_value=mock_ws):
                with pytest.raises(RuntimeError, match="Subscription error"):
                    await rt._connect_and_subscribe()

        asyncio.run(_run())


# ===================================================================
# 9. _fire_change_listeners edge cases
# ===================================================================


class TestWsReceiveLoop:
    """Tests for the WebSocket receive loop."""

    def test_receive_config_changed(self):
        """Receive loop processes config_changed messages."""
        rt = _make_runtime()
        events = []
        rt.on_change(lambda e: events.append(e))

        mock_ws = AsyncMock()
        msg = json.dumps({
            "type": "config_changed",
            "config_id": "cfg-001",
            "changes": [{"key": "retries", "old_value": 10, "new_value": 7}],
        })

        call_count = 0

        async def recv_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return msg
            # Close after first message
            rt._closed = True
            raise websockets.ConnectionClosed(None, None)

        mock_ws.recv = recv_side_effect
        rt._ws = mock_ws

        asyncio.run(rt._ws_receive_loop())
        assert rt.get("retries") == 7
        assert len(events) == 1

    def test_receive_config_deleted(self):
        """Receive loop processes config_deleted messages."""
        rt = _make_runtime()
        mock_ws = AsyncMock()
        msg = json.dumps({
            "type": "config_deleted",
            "config_id": "cfg-001",
            "timestamp": "2026-03-26T15:45:00Z",
        })

        call_count = 0

        async def recv_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return msg
            raise websockets.ConnectionClosed(None, None)

        mock_ws.recv = recv_side_effect
        rt._ws = mock_ws

        asyncio.run(rt._ws_receive_loop())
        assert rt._deleted is True
        assert rt._closed is True

    def test_connection_closed_intentionally_exits(self):
        """When _closed is True and ConnectionClosed fires, loop exits cleanly."""
        rt = _make_runtime()
        rt._closed = True

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=websockets.ConnectionClosed(None, None))
        rt._ws = mock_ws

        # Should exit immediately without reconnecting
        asyncio.run(rt._ws_receive_loop())

    def test_connection_closed_with_deleted_reason_exits(self):
        """ConnectionClosed with 'deleted' reason exits without reconnect."""
        rt = _make_runtime()

        mock_ws = AsyncMock()
        close_frame = websockets.frames.Close(1000, "config deleted")
        exc = websockets.ConnectionClosed(close_frame, None)
        mock_ws.recv = AsyncMock(side_effect=exc)
        rt._ws = mock_ws

        asyncio.run(rt._ws_receive_loop())
        # Should not attempt to reconnect


    def test_unexpected_error_triggers_reconnect(self):
        """An unexpected error in receive loop triggers reconnect."""
        rt = _make_runtime()

        mock_ws = AsyncMock()

        async def recv_side_effect():
            raise RuntimeError("unexpected")

        mock_ws.recv = recv_side_effect
        rt._ws = mock_ws

        async def _run():
            with patch.object(rt, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
                await rt._ws_receive_loop()
                mock_reconnect.assert_called_once()

        asyncio.run(_run())
        assert rt._connection_status == "connecting"

    def test_connection_closed_unexpected_triggers_reconnect(self):
        """An unexpected ConnectionClosed triggers reconnect."""
        rt = _make_runtime()

        mock_ws = AsyncMock()
        exc = websockets.ConnectionClosed(websockets.frames.Close(1006, "abnormal"), None)
        mock_ws.recv = AsyncMock(side_effect=exc)
        rt._ws = mock_ws

        async def _run():
            with patch.object(rt, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
                await rt._ws_receive_loop()
                mock_reconnect.assert_called_once()

        asyncio.run(_run())


class TestWsThreadEntry:
    """Tests for the WebSocket thread entry point."""

    def test_thread_entry_creates_event_loop(self):
        """_ws_thread_entry creates an event loop and runs _ws_main."""
        rt = _make_runtime()
        rt._closed = True  # Prevent actual connection

        with patch.object(rt, "_ws_main", new_callable=AsyncMock) as mock_main:
            rt._ws_thread_entry()
            mock_main.assert_called_once()

        assert rt._ws_loop is not None

    def test_ws_main_handles_connect_failure(self):
        """_ws_main logs warning and enters reconnect on connect failure."""
        rt = _make_runtime()
        rt._closed = True  # Prevent reconnect loop

        async def _run():
            with patch.object(rt, "_connect_and_subscribe", new_callable=AsyncMock,
                              side_effect=OSError("Connection refused")):
                with patch.object(rt, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
                    await rt._ws_main()
                    mock_reconnect.assert_called_once()

        asyncio.run(_run())


class TestReconnectFlow:
    """Tests for the reconnection flow."""

    def test_reconnect_respects_closed_flag(self):
        """_reconnect exits immediately when _closed is set."""
        rt = _make_runtime()
        rt._closed = True

        asyncio.run(rt._reconnect())
        # Should return immediately without trying to connect

    def test_reconnect_succeeds_after_retry(self):
        """_reconnect retries and succeeds on second attempt."""
        rt = _make_runtime()
        attempt = 0

        async def connect_side_effect():
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                raise OSError("Connection refused")
            # Success on second attempt

        async def _run():
            with patch.object(rt, "_connect_and_subscribe", new_callable=AsyncMock,
                              side_effect=connect_side_effect):
                with patch.object(rt, "_resync_cache", new_callable=AsyncMock):
                    # Use a short timeout by closing after a bit
                    async def close_after():
                        await asyncio.sleep(3.5)  # After first retry (1s backoff + margin)
                        rt._closed = True

                    # Don't actually wait — just test the first failure and success
                    with patch("smplkit.config.runtime._BACKOFF_SCHEDULE", [0.01, 0.01]):
                        await rt._reconnect()

        asyncio.run(_run())
        assert attempt >= 2


class TestSyncExit:
    """Tests for __exit__ (sync context manager)."""

    def test_sync_exit_sets_closed(self):
        rt = _make_runtime()
        rt.__exit__(None, None, None)
        assert rt._closed is True
        assert rt.connection_status() == "disconnected"

    def test_sync_exit_with_ws_loop(self):
        """__exit__ tries to close the WS connection via the loop."""
        rt = _make_runtime()
        rt._ws_loop = asyncio.new_event_loop()
        rt._ws = AsyncMock()
        # Should not raise even though loop is not running
        rt.__exit__(None, None, None)
        assert rt._closed is True
        rt._ws_loop.close()


class TestStartWsThread:
    """Tests for _start_ws_thread."""

    def test_start_creates_daemon_thread(self):
        """_start_ws_thread creates and starts a daemon thread."""
        with patch.object(ConfigRuntime, "_ws_thread_entry"):
            rt = ConfigRuntime(
                config_key="test",
                config_id="cfg-001",
                environment="production",
                chain=[{"id": "cfg-001", "values": {}, "environments": {}}],
                api_key="sk_test",
                base_url="https://config.smplkit.com",
            )
            assert rt._ws_thread is not None
            assert rt._ws_thread.daemon is True
            assert rt._ws_thread.name.startswith("smplkit-ws-")


class TestFireChangeListeners:
    def test_no_changes_fires_nothing(self):
        rt = _make_runtime()
        events = []
        rt.on_change(lambda e: events.append(e))
        rt._fire_change_listeners({"a": 1}, {"a": 1}, source="manual")
        assert len(events) == 0

    def test_added_key_fires(self):
        rt = _make_runtime()
        events = []
        rt.on_change(lambda e: events.append(e))
        rt._fire_change_listeners({}, {"a": 1}, source="manual")
        assert len(events) == 1
        assert events[0].key == "a"
        assert events[0].old_value is None
        assert events[0].new_value == 1

    def test_removed_key_fires(self):
        rt = _make_runtime()
        events = []
        rt.on_change(lambda e: events.append(e))
        rt._fire_change_listeners({"a": 1}, {}, source="manual")
        assert len(events) == 1
        assert events[0].key == "a"
        assert events[0].old_value == 1
        assert events[0].new_value is None


# ===================================================================
# 10. _build_ws_url bare URL (no scheme)
# ===================================================================


class TestBuildWsUrlBareHost:
    def test_bare_url_gets_wss_prefix(self):
        """A URL with no http/https scheme gets wss:// prefix."""
        rt = _make_runtime(base_url="config.smplkit.com", api_key="sk_bare")
        url = rt._build_ws_url()
        assert url == "wss://config.smplkit.com/api/ws/v1/configs?api_key=sk_bare"


# ===================================================================
# 11. _ws_thread_entry exception + pending task cleanup
# ===================================================================


class TestWsThreadEntryException:
    def test_exception_in_ws_main_is_caught(self):
        """An exception in _ws_main is caught and the loop is closed."""
        rt = _make_runtime()

        async def boom():
            raise RuntimeError("boom")

        with patch.object(rt, "_ws_main", side_effect=boom):
            rt._ws_thread_entry()

        # Loop should have been closed
        assert rt._ws_loop is not None
        assert rt._ws_loop.is_closed()

    def test_pending_tasks_are_cancelled_on_exit(self):
        """Pending tasks on the ws loop are cancelled before closing."""
        rt = _make_runtime()

        async def leave_pending_task():
            # Create a task that will still be pending when _ws_main returns
            loop = asyncio.get_event_loop()
            loop.create_task(asyncio.sleep(999))

        with patch.object(rt, "_ws_main", side_effect=leave_pending_task):
            rt._ws_thread_entry()

        assert rt._ws_loop is not None
        assert rt._ws_loop.is_closed()


# ===================================================================
# 12. _ws_receive_loop unexpected exception when _closed
# ===================================================================


class TestReceiveLoopExceptionWhenClosed:
    def test_unexpected_exception_when_closed_breaks(self):
        """An unexpected exception when _closed becomes True breaks the loop."""
        rt = _make_runtime()

        mock_ws = AsyncMock()

        async def recv_sets_closed():
            rt._closed = True
            raise RuntimeError("unexpected")

        mock_ws.recv = recv_sets_closed
        rt._ws = mock_ws

        # Should exit without calling _reconnect
        with patch.object(rt, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
            asyncio.run(rt._ws_receive_loop())
            mock_reconnect.assert_not_called()


# ===================================================================
# 13. _reconnect closed during backoff sleep
# ===================================================================


class TestReconnectClosedDuringBackoff:
    def test_reconnect_exits_when_closed_during_sleep(self):
        """_reconnect returns when _closed is set during backoff sleep."""
        rt = _make_runtime()

        original_sleep = asyncio.sleep

        async def close_during_sleep(delay):
            rt._closed = True
            await original_sleep(0)  # yield control

        async def _run():
            with patch.object(rt, "_connect_and_subscribe", new_callable=AsyncMock,
                              side_effect=OSError("refused")):
                with patch("smplkit.config.runtime._BACKOFF_SCHEDULE", [0.01]):
                    with patch("asyncio.sleep", side_effect=close_during_sleep):
                        await rt._reconnect()

        asyncio.run(_run())
        assert rt._closed is True


# ===================================================================
# 14. _resync_cache exception path
# ===================================================================


class TestResyncCacheException:
    def test_resync_cache_catches_fetch_exception(self):
        """_resync_cache logs and swallows exceptions from fetch_chain_fn."""
        def bad_fetch():
            raise RuntimeError("fetch failed")

        rt = _make_runtime(fetch_chain_fn=bad_fetch)
        old_cache = rt.get_all()

        # Should not raise
        asyncio.run(rt._resync_cache())

        # Cache should be unchanged
        assert rt.get_all() == old_cache


# ===================================================================
# 15. close() with ws and ws_loop + thread join
# ===================================================================


class TestCloseMethod:
    def test_close_with_ws_and_loop(self):
        """close() closes ws via run_coroutine_threadsafe and joins thread."""
        rt = _make_runtime()
        loop = asyncio.new_event_loop()
        # Run the loop in a thread so run_coroutine_threadsafe works
        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        rt._ws_loop = loop
        rt._ws = AsyncMock()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        rt._ws_thread = mock_thread

        asyncio.run(rt.close())

        assert rt._closed is True
        assert rt._connection_status == "disconnected"
        mock_thread.join.assert_called_once_with(timeout=2.0)

        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)

    def test_close_exception_in_ws_close_is_swallowed(self):
        """close() swallows exceptions from run_coroutine_threadsafe."""
        rt = _make_runtime()
        rt._ws_loop = MagicMock()
        rt._ws = AsyncMock()
        # Make run_coroutine_threadsafe raise
        with patch("asyncio.run_coroutine_threadsafe", side_effect=RuntimeError("loop closed")):
            asyncio.run(rt.close())

        assert rt._closed is True

    def test_close_joins_alive_thread(self):
        """close() joins the background thread if it's alive."""
        rt = _make_runtime()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        rt._ws_thread = mock_thread

        asyncio.run(rt.close())

        mock_thread.join.assert_called_once_with(timeout=2.0)

    def test_close_skips_join_when_thread_not_alive(self):
        """close() skips join when thread is not alive."""
        rt = _make_runtime()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        rt._ws_thread = mock_thread

        asyncio.run(rt.close())

        mock_thread.join.assert_not_called()


# ===================================================================
# 16. __exit__ exception path
# ===================================================================


class TestSyncExitExceptionPath:
    def test_exit_swallows_exception_from_run_coroutine_threadsafe(self):
        """__exit__ swallows exceptions from run_coroutine_threadsafe."""
        rt = _make_runtime()
        rt._ws_loop = MagicMock()
        rt._ws = AsyncMock()

        with patch("asyncio.run_coroutine_threadsafe", side_effect=RuntimeError("loop closed")):
            rt.__exit__(None, None, None)

        assert rt._closed is True
