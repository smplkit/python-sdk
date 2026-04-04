"""Tests for LoggingClient and AsyncLoggingClient management API and integration."""

from __future__ import annotations

import asyncio
import logging as stdlib_logging
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import SmplNotConnectedError, SmplNotFoundError, SmplValidationError
from smplkit.logging.client import (
    AsyncLoggingClient,
    AsyncSmplLogGroup,
    AsyncSmplLogger,
    LoggingClient,
    SmplLogGroup,
    SmplLogger,
    _LoggerRegistrationBuffer,
    _check_response_status,
)

_TEST_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _make_logger_attrs(*, key="sql", name="SQL Logger", level="DEBUG", group=None, managed=True):
    """Build mock logger attributes."""
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
    """Build mock log group attributes."""
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


def _make_logging_client():
    """Create a LoggingClient with mocked parent."""
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = None
    with patch("smplkit.logging.client.AuthenticatedClient"):
        client = LoggingClient(parent)
    return client


def _make_async_logging_client():
    """Create an AsyncLoggingClient with mocked parent."""
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = None
    with patch("smplkit.logging.client.AuthenticatedClient"):
        client = AsyncLoggingClient(parent)
    return client


# ---------------------------------------------------------------------------
# Logger CRUD
# ---------------------------------------------------------------------------


class TestLoggerCRUD:
    @patch("smplkit.logging.client.create_logger.sync_detailed")
    def test_create(self, mock_create):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_logging_client()
        result = client.create("sql", name="SQL Logger", level="DEBUG")
        assert isinstance(result, SmplLogger)
        assert result.key == "sql"
        assert result.name == "SQL Logger"
        mock_create.assert_called_once()

    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_list(self, mock_list):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        mock_list.return_value = _ok_response(_make_list_parsed([resource]))

        client = _make_logging_client()
        result = client.list()
        assert len(result) == 1
        assert isinstance(result[0], SmplLogger)

    @patch("smplkit.logging.client.get_logger.sync_detailed")
    def test_get(self, mock_get):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)

        client = _make_logging_client()
        result = client.get(_TEST_UUID)
        assert isinstance(result, SmplLogger)
        assert result.id == _TEST_UUID

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save(self, mock_update):
        updated_attrs = _make_logger_attrs(level="ERROR")
        updated_resource = _make_resource(updated_attrs)
        updated_parsed = _make_parsed(updated_resource)
        mock_update.return_value = _ok_response(updated_parsed)

        client = _make_logging_client()
        lg = SmplLogger(
            client,
            id=_TEST_UUID,
            key="sql",
            name="SQL Logger",
            level="DEBUG",
            managed=True,
            group=None,
            environments={},
        )
        lg.level = "ERROR"
        lg.save()

        mock_update.assert_called_once()
        body = mock_update.call_args.kwargs["body"]
        body_attrs = body.data.attributes
        assert body_attrs.name == "SQL Logger"
        assert body_attrs.key == "sql"
        assert body_attrs.level == "ERROR"
        assert body_attrs.managed is True
        assert body_attrs.group is None

    @patch("smplkit.logging.client.delete_logger.sync_detailed")
    def test_delete(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        client = _make_logging_client()
        client.delete(_TEST_UUID)
        mock_delete.assert_called_once()


# ---------------------------------------------------------------------------
# Log Group CRUD
# ---------------------------------------------------------------------------


class TestLogGroupCRUD:
    @patch("smplkit.logging.client.create_log_group.sync_detailed")
    def test_create_group(self, mock_create):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_logging_client()
        result = client.create_group("db-loggers", name="DB Loggers", level="WARN")
        assert isinstance(result, SmplLogGroup)
        assert result.key == "db-loggers"

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    def test_list_groups(self, mock_list):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        mock_list.return_value = _ok_response(_make_list_parsed([resource]))

        client = _make_logging_client()
        result = client.list_groups()
        assert len(result) == 1
        assert isinstance(result[0], SmplLogGroup)

    @patch("smplkit.logging.client.get_log_group.sync_detailed")
    def test_get_group(self, mock_get):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)

        client = _make_logging_client()
        result = client.get_group(_TEST_UUID)
        assert isinstance(result, SmplLogGroup)

    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_group(self, mock_update):
        updated_attrs = _make_group_attrs(level="ERROR")
        updated_resource = _make_resource(updated_attrs)
        updated_parsed = _make_parsed(updated_resource)
        mock_update.return_value = _ok_response(updated_parsed)

        client = _make_logging_client()
        grp = SmplLogGroup(
            client,
            id=_TEST_UUID,
            key="db-loggers",
            name="DB Loggers",
            level="WARN",
            group=None,
            environments={},
        )
        grp.level = "ERROR"
        grp.save()

        mock_update.assert_called_once()
        body = mock_update.call_args.kwargs["body"]
        body_attrs = body.data.attributes
        assert body_attrs.name == "DB Loggers"
        assert body_attrs.key == "db-loggers"
        assert body_attrs.level == "ERROR"
        assert body_attrs.group is None

    @patch("smplkit.logging.client.delete_log_group.sync_detailed")
    def test_delete_group(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        client = _make_logging_client()
        client.delete_group(_TEST_UUID)
        mock_delete.assert_called_once()


# ---------------------------------------------------------------------------
# Logger save() edge cases
# ---------------------------------------------------------------------------


class TestLoggerSave:
    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_sends_all_fields(self, mock_update):
        """save() sends a full-replace PUT with every field present."""
        attrs = _make_logger_attrs(key="sql", name="SQL Logger", level="DEBUG", managed=True)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        lg = SmplLogger(
            client,
            id=_TEST_UUID,
            key="sql",
            name="SQL Logger",
            level="DEBUG",
            managed=True,
            group=None,
            environments={"prod": {"level": "WARN"}},
        )
        lg.save()

        body = mock_update.call_args.kwargs["body"]
        body_attrs = body.data.attributes
        assert body_attrs.name == "SQL Logger"
        assert body_attrs.key == "sql"
        assert body_attrs.level == "DEBUG"
        assert body_attrs.managed is True
        assert body_attrs.group is None

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_with_level_none(self, mock_update):
        """save() with level=None sends null in the PUT body."""
        attrs = _make_logger_attrs(level=None)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        lg = SmplLogger(
            client,
            id=_TEST_UUID,
            key="sql",
            name="SQL Logger",
            level=None,
            managed=True,
            group=None,
            environments={},
        )
        lg.save()

        body = mock_update.call_args.kwargs["body"]
        assert body.data.attributes.level is None

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_with_group_none(self, mock_update):
        """save() with group=None sends null in the PUT body."""
        attrs = _make_logger_attrs(group=None)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        lg = SmplLogger(
            client,
            id=_TEST_UUID,
            key="sql",
            name="SQL Logger",
            level="DEBUG",
            managed=True,
            group=None,
            environments={},
        )
        lg.save()

        body = mock_update.call_args.kwargs["body"]
        assert body.data.attributes.group is None

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_with_managed_false(self, mock_update):
        """save() with managed=False sends false in the PUT body."""
        attrs = _make_logger_attrs(managed=False)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        lg = SmplLogger(
            client,
            id=_TEST_UUID,
            key="sql",
            name="SQL Logger",
            level="DEBUG",
            managed=False,
            group=None,
            environments={},
        )
        lg.save()

        body = mock_update.call_args.kwargs["body"]
        assert body.data.attributes.managed is False

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_updates_self_in_place(self, mock_update):
        """After save(), properties on the model reflect the server response."""
        response_attrs = _make_logger_attrs(key="sql", name="SQL Logger v2", level="ERROR", managed=True)
        response_resource = _make_resource(response_attrs)
        response_parsed = _make_parsed(response_resource)
        mock_update.return_value = _ok_response(response_parsed)

        client = _make_logging_client()
        lg = SmplLogger(
            client,
            id=_TEST_UUID,
            key="sql",
            name="SQL Logger",
            level="DEBUG",
            managed=True,
            group=None,
            environments={},
        )
        lg.level = "ERROR"
        lg.save()

        assert lg.name == "SQL Logger v2"
        assert lg.level == "ERROR"
        assert lg.id == _TEST_UUID


# ---------------------------------------------------------------------------
# Logger create() managed parameter
# ---------------------------------------------------------------------------


class TestLoggerCreateManaged:
    @patch("smplkit.logging.client.create_logger.sync_detailed")
    def test_create_with_managed_true(self, mock_create):
        attrs = _make_logger_attrs(managed=True)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_logging_client()
        client.create("sql", name="SQL Logger", managed=True)

        body = mock_create.call_args.kwargs["body"]
        assert body.data.attributes.managed is True

    @patch("smplkit.logging.client.create_logger.sync_detailed")
    def test_create_with_managed_false(self, mock_create):
        attrs = _make_logger_attrs(managed=False)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_logging_client()
        client.create("sql", name="SQL Logger", managed=False)

        body = mock_create.call_args.kwargs["body"]
        assert body.data.attributes.managed is False

    @patch("smplkit.logging.client.create_logger.sync_detailed")
    def test_create_default_managed(self, mock_create):
        """When managed is not specified, it defaults to False."""
        attrs = _make_logger_attrs(managed=False)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_logging_client()
        client.create("sql", name="SQL Logger")

        body = mock_create.call_args.kwargs["body"]
        assert body.data.attributes.managed is False


# ---------------------------------------------------------------------------
# Group save() edge cases
# ---------------------------------------------------------------------------


class TestGroupSave:
    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_sends_all_fields(self, mock_update):
        """save() sends a full-replace PUT with every field present."""
        attrs = _make_group_attrs(key="db-loggers", name="DB Loggers", level="WARN")
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        grp = SmplLogGroup(
            client,
            id=_TEST_UUID,
            key="db-loggers",
            name="DB Loggers",
            level="WARN",
            group=None,
            environments={"prod": {"level": "ERROR"}},
        )
        grp.save()

        body = mock_update.call_args.kwargs["body"]
        body_attrs = body.data.attributes
        assert body_attrs.name == "DB Loggers"
        assert body_attrs.key == "db-loggers"
        assert body_attrs.level == "WARN"
        assert body_attrs.group is None

    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_with_level_none(self, mock_update):
        """save() with level=None sends null in the PUT body."""
        attrs = _make_group_attrs(level=None)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        grp = SmplLogGroup(
            client,
            id=_TEST_UUID,
            key="db-loggers",
            name="DB Loggers",
            level=None,
            group=None,
            environments={},
        )
        grp.save()

        body = mock_update.call_args.kwargs["body"]
        assert body.data.attributes.level is None

    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_with_group_none(self, mock_update):
        """save() with group=None sends null in the PUT body."""
        attrs = _make_group_attrs(group=None)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_logging_client()
        grp = SmplLogGroup(
            client,
            id=_TEST_UUID,
            key="db-loggers",
            name="DB Loggers",
            level="WARN",
            group=None,
            environments={},
        )
        grp.save()

        body = mock_update.call_args.kwargs["body"]
        assert body.data.attributes.group is None

    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_updates_self_in_place(self, mock_update):
        """After save(), properties on the model reflect the server response."""
        response_attrs = _make_group_attrs(key="db-loggers", name="DB Loggers v2", level="ERROR")
        response_resource = _make_resource(response_attrs)
        response_parsed = _make_parsed(response_resource)
        mock_update.return_value = _ok_response(response_parsed)

        client = _make_logging_client()
        grp = SmplLogGroup(
            client,
            id=_TEST_UUID,
            key="db-loggers",
            name="DB Loggers",
            level="WARN",
            group=None,
            environments={},
        )
        grp.level = "ERROR"
        grp.save()

        assert grp.name == "DB Loggers v2"
        assert grp.level == "ERROR"
        assert grp.id == _TEST_UUID


# ---------------------------------------------------------------------------
# Management works without connect
# ---------------------------------------------------------------------------


class TestManagementWithoutConnect:
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_list_without_connect(self, mock_list):
        mock_list.return_value = _ok_response(_make_list_parsed([]))

        client = _make_logging_client()
        assert client._connected is False
        result = client.list()
        assert result == []


# ---------------------------------------------------------------------------
# Registration buffer
# ---------------------------------------------------------------------------


class TestLoggerRegistrationBuffer:
    def test_add_and_drain(self):
        buf = _LoggerRegistrationBuffer()
        buf.add("com.example", "INFO", "my-service")
        batch = buf.drain()
        assert len(batch) == 1
        assert batch[0] == {"key": "com.example", "level": "INFO", "service": "my-service"}

    def test_dedup(self):
        buf = _LoggerRegistrationBuffer()
        buf.add("com.example", "INFO", "svc")
        buf.add("com.example", "DEBUG", "svc")
        batch = buf.drain()
        assert len(batch) == 1

    def test_service_omitted_when_none(self):
        buf = _LoggerRegistrationBuffer()
        buf.add("com.example", "INFO", None)
        batch = buf.drain()
        assert "service" not in batch[0]

    def test_drain_clears_pending(self):
        buf = _LoggerRegistrationBuffer()
        buf.add("a", "INFO", None)
        buf.drain()
        assert buf.drain() == []

    def test_pending_count(self):
        buf = _LoggerRegistrationBuffer()
        assert buf.pending_count == 0
        buf.add("a", "INFO", None)
        assert buf.pending_count == 1
        buf.add("b", "DEBUG", None)
        assert buf.pending_count == 2

    def test_includes_service_when_provided(self):
        buf = _LoggerRegistrationBuffer()
        buf.add("x", "WARN", "api-gateway")
        batch = buf.drain()
        assert batch[0]["service"] == "api-gateway"


# ---------------------------------------------------------------------------
# Bulk flush (fire-and-forget)
# ---------------------------------------------------------------------------


class TestBulkFlush:
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_flush_sends_batch(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_logging_client()
        client._buffer.add("com.test", "INFO", None)
        client._flush_bulk_sync()
        mock_bulk.assert_called_once()

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_flush_noop_when_empty(self, mock_bulk):
        client = _make_logging_client()
        client._flush_bulk_sync()
        mock_bulk.assert_not_called()

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_flush_fire_and_forget(self, mock_bulk):
        """Flush should not raise even if the HTTP call fails."""
        mock_bulk.side_effect = Exception("network error")
        client = _make_logging_client()
        client._buffer.add("com.test", "INFO", None)
        # Should not raise
        client._flush_bulk_sync()


# ---------------------------------------------------------------------------
# Level application
# ---------------------------------------------------------------------------


class TestLevelApplication:
    def test_managed_logger_gets_level_applied(self):
        client = _make_logging_client()
        test_name = "test.apply.managed_001"
        client._name_map[test_name] = "test.apply.managed_001"
        client._loggers_cache = {
            "test.apply.managed_001": {
                "key": "test.apply.managed_001",
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}

        client._apply_levels()
        lg = stdlib_logging.getLogger(test_name)
        assert lg.level == 40  # ERROR

    def test_unmanaged_logger_not_touched(self):
        client = _make_logging_client()
        test_name = "test.apply.unmanaged_002"
        lg = stdlib_logging.getLogger(test_name)
        lg.setLevel(stdlib_logging.DEBUG)
        client._name_map[test_name] = "test.apply.unmanaged_002"
        client._loggers_cache = {
            "test.apply.unmanaged_002": {
                "key": "test.apply.unmanaged_002",
                "level": "ERROR",
                "group": None,
                "managed": False,
                "environments": {},
            }
        }
        client._groups_cache = {}

        client._apply_levels()
        assert lg.level == stdlib_logging.DEBUG  # Unchanged

    def test_logger_in_server_not_in_runtime(self):
        client = _make_logging_client()
        # Logger known to server but NOT in name_map (not in this runtime)
        client._loggers_cache = {
            "some.remote.logger": {
                "key": "some.remote.logger",
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        # Should not raise
        client._apply_levels()


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_refresh_requires_connect(self):
        client = _make_logging_client()
        with pytest.raises(SmplNotConnectedError):
            client.refresh()

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_refresh_fetches_and_applies(self, mock_loggers, mock_groups):
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_logging_client()
        client._connected = True
        client.refresh()
        mock_loggers.assert_called_once()
        mock_groups.assert_called_once()


# ---------------------------------------------------------------------------
# Integration: connect flow
# ---------------------------------------------------------------------------


class TestConnectFlow:
    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    @patch("smplkit.logging.client.install_discovery_patch")
    @patch("smplkit.logging.client.discover_existing_loggers")
    def test_connect_runs_full_flow(self, mock_discover, mock_patch, mock_bulk, mock_loggers, mock_groups):
        mock_discover.return_value = [("root", 30), ("myapp.db", 10)]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_logging_client()
        client._connect_internal()

        assert client._connected is True
        mock_discover.assert_called_once()
        mock_patch.assert_called_once()
        mock_bulk.assert_called_once()
        mock_loggers.assert_called_once()
        mock_groups.assert_called_once()
        # Cleanup timer
        client._close()

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    @patch("smplkit.logging.client.install_discovery_patch")
    @patch("smplkit.logging.client.discover_existing_loggers")
    def test_connect_applies_managed_levels(self, mock_discover, mock_patch, mock_bulk, mock_loggers, mock_groups):
        test_name = "test.connect.managed_apply_flow"
        stdlib_logging.getLogger(test_name).setLevel(stdlib_logging.DEBUG)

        mock_discover.return_value = [(test_name, stdlib_logging.DEBUG)]
        mock_bulk.return_value = _ok_response()

        # Server says this logger is managed with level ERROR
        logger_attrs = _make_logger_attrs(key=test_name, level="ERROR", managed=True)
        logger_resource = _make_resource(logger_attrs)
        mock_loggers.return_value = _ok_response(_make_list_parsed([logger_resource]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_logging_client()
        client._connect_internal()

        lg = stdlib_logging.getLogger(test_name)
        assert lg.level == stdlib_logging.ERROR
        client._close()


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------


class TestClose:
    @patch("smplkit.logging.client.uninstall_discovery_patch")
    def test_close_uninstalls_patch(self, mock_uninstall):
        client = _make_logging_client()
        client._close()
        mock_uninstall.assert_called_once()

    def test_close_cancels_timer(self):
        client = _make_logging_client()
        timer = MagicMock()
        client._flush_timer = timer
        client._close()
        timer.cancel.assert_called_once()


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestCheckResponseStatus:
    def test_404_raises_not_found(self):
        with pytest.raises(SmplNotFoundError):
            _check_response_status(HTTPStatus.NOT_FOUND, b"not found")

    def test_422_raises_validation(self):
        with pytest.raises(SmplValidationError):
            _check_response_status(HTTPStatus.UNPROCESSABLE_ENTITY, b"validation error")

    def test_200_no_raise(self):
        _check_response_status(HTTPStatus.OK, b"")


# ---------------------------------------------------------------------------
# Async CRUD (smoke tests)
# ---------------------------------------------------------------------------


class TestAsyncLoggerCRUD:
    @patch("smplkit.logging.client.create_logger.asyncio_detailed")
    def test_create(self, mock_create):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_async_logging_client()
        result = asyncio.run(client.create("sql", name="SQL Logger"))
        assert isinstance(result, AsyncSmplLogger)

    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_list(self, mock_list):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        mock_list.return_value = _ok_response(_make_list_parsed([resource]))

        client = _make_async_logging_client()
        result = asyncio.run(client.list())
        assert len(result) == 1

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get(self, mock_get):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_get.return_value = _ok_response(parsed)

        client = _make_async_logging_client()
        result = asyncio.run(client.get(_TEST_UUID))
        assert isinstance(result, AsyncSmplLogger)

    @patch("smplkit.logging.client.delete_logger.asyncio_detailed")
    def test_delete(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        client = _make_async_logging_client()
        asyncio.run(client.delete(_TEST_UUID))
        mock_delete.assert_called_once()


class TestAsyncLogGroupCRUD:
    @patch("smplkit.logging.client.create_log_group.asyncio_detailed")
    def test_create_group(self, mock_create):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_async_logging_client()
        result = asyncio.run(client.create_group("db-loggers", name="DB Loggers"))
        assert isinstance(result, AsyncSmplLogGroup)

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    def test_list_groups(self, mock_list):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        mock_list.return_value = _ok_response(_make_list_parsed([resource]))

        client = _make_async_logging_client()
        result = asyncio.run(client.list_groups())
        assert len(result) == 1


class TestAsyncRefresh:
    def test_refresh_requires_connect(self):
        client = _make_async_logging_client()
        with pytest.raises(SmplNotConnectedError):
            asyncio.run(client.refresh())
