"""Additional sync client tests for complete coverage."""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import SmplNotFoundError, SmplValidationError
from smplkit.logging.client import LoggingClient, SmplLogGroup, SmplLogger


_TEST_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _make_logger_attrs(*, name="SQL Logger", level="DEBUG", group=None, managed=True):
    from smplkit._generated.logging.types import UNSET

    attrs = MagicMock()
    attrs.name = name
    attrs.level = level
    attrs.group = group if group is not None else UNSET
    attrs.managed = managed
    attrs.sources = UNSET
    attrs.environments = UNSET
    attrs.created_at = UNSET
    attrs.updated_at = UNSET
    return attrs


def _make_group_attrs(*, name="DB Loggers", level="WARN", parent_id=None):
    from smplkit._generated.logging.types import UNSET

    attrs = MagicMock()
    attrs.name = name
    attrs.level = level
    attrs.parent_id = parent_id if parent_id is not None else UNSET
    attrs.environments = UNSET
    attrs.created_at = UNSET
    attrs.updated_at = UNSET
    return attrs


def _make_resource(attrs, id=_TEST_UUID):
    resource = MagicMock()
    resource.id = id
    resource.attributes = attrs
    return resource


def _make_parsed(resource):
    parsed = MagicMock()
    parsed.data = resource
    return parsed


def _make_list_parsed(resources):
    parsed = MagicMock()
    parsed.data = resources
    return parsed


def _ok_response(parsed=None, status=HTTPStatus.OK):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b""
    resp.parsed = parsed
    return resp


def _make_logging_client(**kwargs):
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = kwargs.get("service", None)
    with patch("smplkit.logging.client.AuthenticatedClient"):
        client = LoggingClient(parent)
    return client


class TestSyncOnNewLogger:
    def test_callback_adds_to_buffer(self):
        client = _make_logging_client()
        client._on_new_logger("my.sync.logger", 20, 20)
        assert client._buffer.pending_count == 1
        assert "my.sync.logger" in client._name_map

    def test_callback_applies_level_when_connected(self):
        client = _make_logging_client()
        client._connected = True
        test_name = "test.sync.on_new.managed_aaa"
        mock_adapter = MagicMock()
        client._adapters = [mock_adapter]
        client._loggers_cache = {
            test_name: {
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._on_new_logger(test_name, 20, 20)
        mock_adapter.apply_level.assert_called_once_with(test_name, 40)

    @patch("smplkit.logging.client.threading.Thread")
    def test_callback_triggers_flush_at_threshold(self, mock_thread):
        client = _make_logging_client()
        for i in range(50):
            client._buffer.add(f"logger.{i}", "INFO", "INFO", None, None)
        client._buffer.drain()
        for i in range(50):
            client._buffer.add(f"logger.thresh.{i}", "INFO", "INFO", None, None)
        client._on_new_logger("trigger.flush", 20, 20)
        mock_thread.assert_called()


class TestSyncScheduleFlush:
    def test_schedule_creates_timer(self):
        client = _make_logging_client()
        client._schedule_flush()
        assert client._flush_timer is not None
        client._flush_timer.cancel()


class TestSyncConnectWithService:
    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_with_service(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = [("root", 30)]
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_logging_client(service="api-svc")
        client._connect_internal()
        assert client._connected is True
        client._close()

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_fetch_failure_resilient(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = []
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.side_effect = Exception("network error")

        client = _make_logging_client()
        client._connect_internal()
        assert client._connected is True
        client._close()


class TestSyncFetchAndApply:
    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_fetches_and_caches(self, mock_loggers, mock_groups):
        logger_attrs = _make_logger_attrs(managed=True)
        logger_resource = _make_resource(logger_attrs, id="com.test")
        mock_loggers.return_value = _ok_response(_make_list_parsed([logger_resource]))

        group_attrs = _make_group_attrs()
        group_resource = _make_resource(group_attrs, id="grp-1")
        mock_groups.return_value = _ok_response(_make_list_parsed([group_resource]))

        client = _make_logging_client()
        client._fetch_and_apply()

        assert "com.test" in client._loggers_cache
        assert "grp-1" in client._groups_cache

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_group_parent_id_stored_as_group_key(self, mock_loggers, mock_groups):
        """groups_cache['group'] must come from parent_id, not a nonexistent 'group' attr."""
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))

        group_attrs = _make_group_attrs(parent_id="parent-grp-id")
        group_resource = _make_resource(group_attrs, id="child-grp")
        mock_groups.return_value = _ok_response(_make_list_parsed([group_resource]))

        client = _make_logging_client()
        client._fetch_and_apply()

        assert client._groups_cache["child-grp"]["group"] == "parent-grp-id"


class TestSyncErrorPaths:
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_save_new_logger_bulk_raises_connection_error(self, mock_bulk):
        import httpx
        mock_bulk.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError
        lg = client.management.new("sql", name="SQL")
        with pytest.raises(SmplConnectionError):
            lg.save()

    @patch("smplkit.logging.client.get_logger.sync_detailed")
    def test_get_null_parsed(self, mock_get):
        mock_get.return_value = _ok_response(None, HTTPStatus.OK)
        client = _make_logging_client()
        with pytest.raises(SmplNotFoundError):
            client.management.get("sql")

    @patch("smplkit.logging.client.create_log_group.sync_detailed")
    def test_save_group_create_null_parsed(self, mock_create):
        mock_create.return_value = _ok_response(None, HTTPStatus.CREATED)
        client = _make_logging_client()
        grp = client.management.new_group("db", name="DB")
        with pytest.raises(SmplValidationError):
            grp.save()

    @patch("smplkit.logging.client.get_log_group.sync_detailed")
    def test_get_group_null_parsed(self, mock_get):
        mock_get.return_value = _ok_response(None, HTTPStatus.OK)
        client = _make_logging_client()
        with pytest.raises(SmplNotFoundError):
            client.management.get_group("db")

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_logger_null_parsed(self, mock_update):
        mock_update.return_value = _ok_response(None)
        client = _make_logging_client()
        lg = SmplLogger(client, id=_TEST_UUID, name="SQL Logger", created_at="2026-01-01T00:00:00Z")
        with pytest.raises(SmplValidationError):
            client._save_logger(lg)

    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_group_null_parsed(self, mock_update):
        mock_update.return_value = _ok_response(None)
        client = _make_logging_client()
        grp = SmplLogGroup(client, id=_TEST_UUID, name="DB Loggers", created_at="2026-01-01T00:00:00Z")
        with pytest.raises(SmplValidationError):
            client._save_group(grp)

    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_list_network_error(self, mock_list):
        import httpx

        mock_list.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError

        with pytest.raises(SmplConnectionError):
            client.management.list()

    @patch("smplkit.logging.client.get_logger.sync_detailed")
    def test_get_network_error(self, mock_get):
        import httpx

        mock_get.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError

        with pytest.raises(SmplConnectionError):
            client.management.get("sql")

    @patch("smplkit.logging.client.delete_logger.sync_detailed")
    def test_delete_network_error(self, mock_delete):
        import httpx

        mock_delete.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError

        with pytest.raises(SmplConnectionError):
            client.management.delete("sql")

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    def test_list_groups_network_error(self, mock_list):
        import httpx

        mock_list.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError

        with pytest.raises(SmplConnectionError):
            client.management.list_groups()

    @patch("smplkit.logging.client.get_log_group.sync_detailed")
    def test_get_group_network_error(self, mock_get):
        import httpx

        mock_get.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError

        with pytest.raises(SmplConnectionError):
            client.management.get_group("db")

    @patch("smplkit.logging.client.delete_log_group.sync_detailed")
    def test_delete_group_network_error(self, mock_delete):
        import httpx

        mock_delete.side_effect = httpx.ConnectError("refused")
        client = _make_logging_client()
        from smplkit._errors import SmplConnectionError

        with pytest.raises(SmplConnectionError):
            client.management.delete_group("db")
