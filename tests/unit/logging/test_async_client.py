"""Tests for AsyncLoggingClient — covers all async code paths."""

from __future__ import annotations

import asyncio
import logging as stdlib_logging
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import SmplNotConnectedError, SmplNotFoundError, SmplValidationError
from smplkit.logging.client import (
    AsyncLoggingClient,
    SmplLogGroup,
    SmplLogger,
)


_TEST_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _make_logger_attrs(*, key="sql", name="SQL Logger", level="DEBUG", group=None, managed=True):
    from smplkit._generated.logging.types import UNSET

    attrs = MagicMock()
    attrs.key = key
    attrs.name = name
    attrs.level = level
    attrs.group = group if group is not None else UNSET
    attrs.managed = managed
    attrs.sources = UNSET
    attrs.environments = UNSET
    attrs.created_at = UNSET
    attrs.updated_at = UNSET
    return attrs


def _make_group_attrs(*, key="db-loggers", name="DB Loggers", level="WARN", group=None):
    from smplkit._generated.logging.types import UNSET

    attrs = MagicMock()
    attrs.key = key
    attrs.name = name
    attrs.level = level
    attrs.group = group if group is not None else UNSET
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


def _make_async_logging_client(**kwargs):
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = kwargs.get("service", None)
    with patch("smplkit.logging.client.AuthenticatedClient"):
        client = AsyncLoggingClient(parent)
    return client


# --- Logger CRUD ---


class TestAsyncLoggerUpdate:
    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_update(self, mock_get, mock_update):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)

        updated_attrs = _make_logger_attrs(level="ERROR")
        updated_resource = _make_resource(updated_attrs)
        updated_parsed = _make_parsed(updated_resource)
        mock_update.return_value = _ok_response(updated_parsed)

        client = _make_async_logging_client()
        result = asyncio.run(client.update(_TEST_UUID, level="ERROR"))
        assert isinstance(result, SmplLogger)


# --- Log Group CRUD ---


class TestAsyncLogGroupGet:
    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group(self, mock_get):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)

        client = _make_async_logging_client()
        result = asyncio.run(client.get_group(_TEST_UUID))
        assert isinstance(result, SmplLogGroup)


class TestAsyncLogGroupUpdate:
    @patch("smplkit.logging.client.update_log_group.asyncio_detailed")
    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_update_group(self, mock_get, mock_update):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)

        updated_attrs = _make_group_attrs(level="ERROR")
        updated_resource = _make_resource(updated_attrs)
        updated_parsed = _make_parsed(updated_resource)
        mock_update.return_value = _ok_response(updated_parsed)

        client = _make_async_logging_client()
        result = asyncio.run(client.update_group(_TEST_UUID, level="ERROR"))
        assert isinstance(result, SmplLogGroup)


class TestAsyncLogGroupDelete:
    @patch("smplkit.logging.client.delete_log_group.asyncio_detailed")
    def test_delete_group(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        client = _make_async_logging_client()
        asyncio.run(client.delete_group(_TEST_UUID))
        mock_delete.assert_called_once()


# --- Connect flow ---


class TestAsyncConnectFlow:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.install_discovery_patch")
    @patch("smplkit.logging.client.discover_existing_loggers")
    def test_connect_full_flow(
        self, mock_discover, mock_patch, mock_bulk, mock_loggers, mock_groups
    ):
        mock_discover.return_value = [("root", 30), ("myapp.db", 10)]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        asyncio.run(client._connect_internal())

        assert client._connected is True
        mock_discover.assert_called_once()
        mock_patch.assert_called_once()
        mock_bulk.assert_called_once()
        client._close()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.install_discovery_patch")
    @patch("smplkit.logging.client.discover_existing_loggers")
    def test_connect_with_service(
        self, mock_discover, mock_patch, mock_bulk, mock_loggers, mock_groups
    ):
        mock_discover.return_value = [("root", 30)]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client(service="api-gateway")
        asyncio.run(client._connect_internal())

        assert client._connected is True
        client._close()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.install_discovery_patch")
    @patch("smplkit.logging.client.discover_existing_loggers")
    def test_connect_fetch_failure_is_resilient(
        self, mock_discover, mock_patch, mock_bulk, mock_loggers, mock_groups
    ):
        mock_discover.return_value = []
        mock_bulk.return_value = _ok_response()
        mock_loggers.side_effect = Exception("network error")

        client = _make_async_logging_client()
        # Should not raise
        asyncio.run(client._connect_internal())
        assert client._connected is True
        client._close()


# --- Refresh ---


class TestAsyncRefreshApplies:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_refresh_fetches_and_applies(self, mock_loggers, mock_groups):
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        client._connected = True
        asyncio.run(client.refresh())
        mock_loggers.assert_called_once()
        mock_groups.assert_called_once()


# --- Bulk flush ---


class TestAsyncBulkFlush:
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    def test_async_flush(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", None)
        asyncio.run(client._flush_bulk_async())
        mock_bulk.assert_called_once()

    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    def test_async_flush_empty(self, mock_bulk):
        client = _make_async_logging_client()
        asyncio.run(client._flush_bulk_async())
        mock_bulk.assert_not_called()

    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    def test_async_flush_error_swallowed(self, mock_bulk):
        mock_bulk.side_effect = Exception("fail")
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", None)
        asyncio.run(client._flush_bulk_async())

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_sync_flush_on_timer(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", None)
        client._flush_bulk_sync()
        mock_bulk.assert_called_once()

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_sync_flush_empty(self, mock_bulk):
        client = _make_async_logging_client()
        client._flush_bulk_sync()
        mock_bulk.assert_not_called()

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_sync_flush_error_swallowed(self, mock_bulk):
        mock_bulk.side_effect = Exception("fail")
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", None)
        client._flush_bulk_sync()


# --- On new logger callback ---


class TestAsyncOnNewLogger:
    def test_callback_adds_to_buffer(self):
        client = _make_async_logging_client()
        client._on_new_logger("my.new.logger", 20)
        assert client._buffer.pending_count == 1
        assert "my.new.logger" in client._name_map

    def test_callback_applies_level_when_connected(self):
        client = _make_async_logging_client()
        client._connected = True
        test_name = "test.async.on_new.managed_xyz"
        client._loggers_cache = {
            test_name: {
                "key": test_name,
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._on_new_logger(test_name, 20)
        lg = stdlib_logging.getLogger(test_name)
        assert lg.level == 40  # ERROR


# --- Level application ---


class TestAsyncLevelApplication:
    def test_apply_levels_managed(self):
        client = _make_async_logging_client()
        test_name = "test.async.apply.managed_111"
        client._name_map[test_name] = test_name
        client._loggers_cache = {
            test_name: {
                "key": test_name,
                "level": "WARN",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._apply_levels()
        lg = stdlib_logging.getLogger(test_name)
        assert lg.level == 30

    def test_apply_levels_unmanaged_skipped(self):
        client = _make_async_logging_client()
        test_name = "test.async.apply.unmanaged_222"
        lg = stdlib_logging.getLogger(test_name)
        lg.setLevel(stdlib_logging.DEBUG)
        client._name_map[test_name] = test_name
        client._loggers_cache = {
            test_name: {
                "key": test_name,
                "level": "ERROR",
                "group": None,
                "managed": False,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._apply_levels()
        assert lg.level == stdlib_logging.DEBUG

    def test_apply_levels_not_in_runtime_skipped(self):
        client = _make_async_logging_client()
        client._loggers_cache = {
            "some.remote": {
                "key": "some.remote",
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._apply_levels()  # Should not raise


# --- Close ---


class TestAsyncClose:
    @patch("smplkit.logging.client.uninstall_discovery_patch")
    def test_close_uninstalls_patch(self, mock_uninstall):
        client = _make_async_logging_client()
        client._close()
        mock_uninstall.assert_called_once()

    def test_close_cancels_timer(self):
        client = _make_async_logging_client()
        timer = MagicMock()
        client._flush_timer = timer
        client._close()
        timer.cancel.assert_called_once()
        assert client._flush_timer is None


# --- Schedule flush ---


class TestAsyncScheduleFlush:
    def test_schedule_creates_timer(self):
        client = _make_async_logging_client()
        client._schedule_flush()
        assert client._flush_timer is not None
        client._flush_timer.cancel()


# --- Fetch and apply ---


class TestAsyncFetchAndApply:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_fetches_and_caches(self, mock_loggers, mock_groups):
        logger_attrs = _make_logger_attrs(key="com.test", managed=True)
        logger_resource = _make_resource(logger_attrs)
        mock_loggers.return_value = _ok_response(_make_list_parsed([logger_resource]))

        group_attrs = _make_group_attrs()
        group_resource = _make_resource(group_attrs, id="grp-1")
        mock_groups.return_value = _ok_response(_make_list_parsed([group_resource]))

        client = _make_async_logging_client()
        asyncio.run(client._fetch_and_apply())

        assert "com.test" in client._loggers_cache
        assert "grp-1" in client._groups_cache


# --- Error paths ---


class TestAsyncErrorPaths:
    @patch("smplkit.logging.client.create_logger.asyncio_detailed")
    def test_create_validation_error(self, mock_create):
        mock_create.return_value = _ok_response(None, HTTPStatus.CREATED)

        client = _make_async_logging_client()
        with pytest.raises(SmplValidationError):
            asyncio.run(client.create("sql", name="SQL"))

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get_not_found(self, mock_get):
        mock_get.return_value = _ok_response(None, HTTPStatus.OK)

        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.get(_TEST_UUID))

    @patch("smplkit.logging.client.create_log_group.asyncio_detailed")
    def test_create_group_validation_error(self, mock_create):
        mock_create.return_value = _ok_response(None, HTTPStatus.CREATED)

        client = _make_async_logging_client()
        with pytest.raises(SmplValidationError):
            asyncio.run(client.create_group("db", name="DB"))

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group_not_found(self, mock_get):
        mock_get.return_value = _ok_response(None, HTTPStatus.OK)

        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.get_group(_TEST_UUID))

    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_update_validation_error(self, mock_get, mock_update):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)
        mock_update.return_value = _ok_response(None)

        client = _make_async_logging_client()
        with pytest.raises(SmplValidationError):
            asyncio.run(client.update(_TEST_UUID, level="ERROR"))

    @patch("smplkit.logging.client.update_log_group.asyncio_detailed")
    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_update_group_validation_error(self, mock_get, mock_update):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)
        mock_update.return_value = _ok_response(None)

        client = _make_async_logging_client()
        with pytest.raises(SmplValidationError):
            asyncio.run(client.update_group(_TEST_UUID, level="ERROR"))

    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_list_empty_parsed(self, mock_list):
        mock_list.return_value = _ok_response(None)

        client = _make_async_logging_client()
        result = asyncio.run(client.list())
        assert result == []

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    def test_list_groups_empty_parsed(self, mock_list):
        mock_list.return_value = _ok_response(None)

        client = _make_async_logging_client()
        result = asyncio.run(client.list_groups())
        assert result == []
