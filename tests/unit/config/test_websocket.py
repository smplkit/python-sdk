"""Tests for ConfigRuntime integration with SharedWebSocket."""

import asyncio
import threading
from unittest.mock import MagicMock

from smplkit.config.runtime import ConfigRuntime


# ---------------------------------------------------------------------------
# Helper to build a ConfigRuntime without a real SharedWebSocket
# ---------------------------------------------------------------------------


def _make_ws_manager():
    """Create a mock SharedWebSocket."""
    ws = MagicMock()
    ws.connection_status = "connected"
    ws.on = MagicMock()
    ws.off = MagicMock()
    return ws


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
    ws_manager=None,
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
    return ConfigRuntime(
        config_key=config_key,
        config_id=config_id,
        environment=environment,
        chain=chain,
        api_key=api_key,
        base_url=base_url,
        fetch_chain_fn=fetch_chain_fn,
        ws_manager=ws_manager,
    )


# ===================================================================
# 1. SharedWebSocket registration
# ===================================================================


class TestSharedWsRegistration:
    def test_registers_listeners_on_init(self):
        """ConfigRuntime registers config_changed and config_deleted listeners."""
        ws = _make_ws_manager()
        rt = _make_runtime(ws_manager=ws)
        assert ws.on.call_count == 2
        ws.on.assert_any_call("config_changed", rt._handle_config_changed)
        ws.on.assert_any_call("config_deleted", rt._handle_config_deleted)

    def test_no_ws_manager_no_registration(self):
        """ConfigRuntime without ws_manager does not crash."""
        rt = _make_runtime(ws_manager=None)
        assert rt._ws_manager is None

    def test_close_unregisters_listeners(self):
        """close() unregisters handlers from the shared WebSocket."""
        ws = _make_ws_manager()
        rt = _make_runtime(ws_manager=ws)
        asyncio.run(rt.close())
        assert ws.off.call_count == 2
        ws.off.assert_any_call("config_changed", rt._handle_config_changed)
        ws.off.assert_any_call("config_deleted", rt._handle_config_deleted)

    def test_sync_exit_unregisters_listeners(self):
        """__exit__ unregisters handlers from the shared WebSocket."""
        ws = _make_ws_manager()
        rt = _make_runtime(ws_manager=ws)
        rt.__exit__(None, None, None)
        assert ws.off.call_count == 2


# ===================================================================
# 2. config_changed handling (re-fetch based)
# ===================================================================


class TestHandleConfigChanged:
    def test_refetch_updates_cache_and_fires_listener(self):
        """config_changed triggers re-fetch and fires listeners."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 7, "name": "test"},
                "environments": {"production": {"values": {"retries": 7}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)
        assert rt.get("retries") == 10

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": "cfg-001",
            }
        )

        mock_fetch.assert_called_once()
        assert rt.get("retries") == 7
        assert len(events) == 1
        assert events[0].key == "retries"
        assert events[0].source == "websocket"

    def test_parent_change_triggers_refetch(self):
        """config_changed for a parent config triggers re-fetch."""
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

        new_chain = [
            {
                "id": child_id,
                "values": {"child_key": "child_val"},
                "environments": {},
            },
            {
                "id": parent_id,
                "values": {"inherited_key": "new_parent_val"},
                "environments": {},
            },
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(config_id=child_id, chain=chain, fetch_chain_fn=mock_fetch)
        assert rt.get("inherited_key") == "old_parent_val"

        events = []
        rt.on_change(lambda e: events.append(e))

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": parent_id,
            }
        )

        assert rt.get("inherited_key") == "new_parent_val"
        assert len(events) == 1

    def test_unknown_config_id_is_ignored(self):
        """config_changed for an unknown config_id is silently ignored."""
        rt = _make_runtime()
        old_cache = rt.get_all()

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": "unknown-id",
            }
        )

        assert rt.get_all() == old_cache

    def test_no_fetch_fn_is_noop(self):
        """config_changed without fetch_chain_fn is a no-op."""
        rt = _make_runtime(fetch_chain_fn=None)
        old_cache = rt.get_all()

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": "cfg-001",
            }
        )

        assert rt.get_all() == old_cache

    def test_fetch_exception_is_caught(self):
        """config_changed swallows exceptions from fetch_chain_fn."""

        def bad_fetch():
            raise RuntimeError("fetch failed")

        rt = _make_runtime(fetch_chain_fn=bad_fetch)
        old_cache = rt.get_all()

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": "cfg-001",
            }
        )

        assert rt.get_all() == old_cache

    def test_key_specific_listener_only_fires_for_matching_key(self):
        """Key-specific listener fires only for its key, not others."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 5, "name": "updated"},
                "environments": {"production": {"values": {"retries": 10}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)

        retries_events = []
        all_events = []
        rt.on_change(lambda e: retries_events.append(e), key="retries")
        rt.on_change(lambda e: all_events.append(e))

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": "cfg-001",
            }
        )

        assert len(retries_events) == 0  # retries didn't change
        assert len(all_events) == 1  # name changed

    def test_listener_exception_is_caught_other_listeners_fire(self):
        """A broken listener doesn't prevent other listeners from firing."""
        new_chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 7, "name": "test"},
                "environments": {"production": {"values": {}}},
            }
        ]
        mock_fetch = MagicMock(return_value=new_chain)
        rt = _make_runtime(fetch_chain_fn=mock_fetch)

        good_events = []

        def bad_listener(event):
            raise ValueError("boom")

        rt.on_change(bad_listener)
        rt.on_change(lambda e: good_events.append(e))

        rt._handle_config_changed(
            {
                "event": "config_changed",
                "config_id": "cfg-001",
            }
        )

        assert len(good_events) >= 1


# ===================================================================
# 3. config_deleted handling
# ===================================================================


class TestHandleConfigDeleted:
    def test_sets_closed_and_deleted(self):
        rt = _make_runtime()
        rt._handle_config_deleted(
            {
                "event": "config_deleted",
                "config_id": "cfg-001",
            }
        )
        assert rt._closed is True
        assert rt._deleted is True

    def test_get_still_works_after_deletion(self):
        """get() returns stale cache after deletion (graceful degradation)."""
        rt = _make_runtime()
        rt._handle_config_deleted(
            {
                "event": "config_deleted",
                "config_id": "cfg-001",
            }
        )
        assert rt.get("retries") == 10

    def test_unrelated_config_deletion_ignored(self):
        """config_deleted for a config not in our chain is ignored."""
        rt = _make_runtime()
        rt._handle_config_deleted(
            {
                "event": "config_deleted",
                "config_id": "other-cfg",
            }
        )
        assert rt._closed is False
        assert rt._deleted is False


# ===================================================================
# 4. Connection status
# ===================================================================


class TestConnectionStatus:
    def test_delegates_to_ws_manager(self):
        ws = _make_ws_manager()
        ws.connection_status = "connected"
        rt = _make_runtime(ws_manager=ws)
        assert rt.connection_status() == "connected"

    def test_disconnected_without_ws_manager(self):
        rt = _make_runtime(ws_manager=None)
        assert rt.connection_status() == "disconnected"

    def test_reflects_ws_manager_status_changes(self):
        ws = _make_ws_manager()
        ws.connection_status = "reconnecting"
        rt = _make_runtime(ws_manager=ws)
        assert rt.connection_status() == "reconnecting"


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
        asyncio.run(rt.refresh())


# ===================================================================
# 6. Thread safety
# ===================================================================


class TestThreadSafety:
    def test_concurrent_gets_while_cache_updates(self):
        """Concurrent get() calls while cache is being refreshed don't raise."""
        chain = [
            {
                "id": "cfg-001",
                "values": {"retries": 5, "name": "test"},
                "environments": {"production": {"values": {"retries": 10}}},
            }
        ]

        call_count = 0

        def fetch_chain():
            nonlocal call_count
            call_count += 1
            return [
                {
                    "id": "cfg-001",
                    "values": {"retries": call_count, "name": "test"},
                    "environments": {"production": {"values": {}}},
                }
            ]

        rt = _make_runtime(chain=chain, fetch_chain_fn=fetch_chain)

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

        for _ in range(50):
            rt._handle_config_changed(
                {
                    "event": "config_changed",
                    "config_id": "cfg-001",
                }
            )

        stop.set()
        for t in threads:
            t.join(timeout=2.0)

        assert errors == []


# ===================================================================
# 7. _fire_change_listeners edge cases
# ===================================================================


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
# 8. Close and context manager
# ===================================================================


class TestCloseMethod:
    def test_close_sets_closed(self):
        rt = _make_runtime()
        asyncio.run(rt.close())
        assert rt._closed is True

    def test_sync_exit_sets_closed(self):
        rt = _make_runtime()
        rt.__exit__(None, None, None)
        assert rt._closed is True
