"""Tests for AsyncLoggingClient — covers all async code paths."""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from smplkit import LogLevel
from smplkit._errors import SmplNotFoundError, SmplValidationError
from smplkit.logging.client import (
    AsyncLoggingClient,
    AsyncSmplLogGroup,
    AsyncSmplLogger,
)


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


def _make_async_logging_client(**kwargs):
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = kwargs.get("service", None)
    with patch("smplkit.logging.client.AuthenticatedClient"):
        client = AsyncLoggingClient(parent)
    return client


# ---------------------------------------------------------------------------
# new() — factory for unsaved async loggers
# ---------------------------------------------------------------------------


class TestAsyncNew:
    def test_new_returns_unsaved_logger(self):
        client = _make_async_logging_client()
        lg = client.management.new("sql")
        assert isinstance(lg, AsyncSmplLogger)
        assert lg.id == "sql"
        assert lg.managed is False

    def test_new_with_name(self):
        client = _make_async_logging_client()
        lg = client.management.new("sql", name="SQL Logger")
        assert lg.name == "SQL Logger"

    def test_new_auto_generates_name(self):
        client = _make_async_logging_client()
        lg = client.management.new("checkout-v2")
        assert lg.name == "Checkout V2"

    def test_new_with_managed(self):
        client = _make_async_logging_client()
        lg = client.management.new("sql", managed=True)
        assert lg.managed is True


# ---------------------------------------------------------------------------
# new_group() — factory for unsaved async log groups
# ---------------------------------------------------------------------------


class TestAsyncNewGroup:
    def test_new_group_returns_unsaved(self):
        client = _make_async_logging_client()
        grp = client.management.new_group("db-loggers")
        assert isinstance(grp, AsyncSmplLogGroup)
        assert grp.id == "db-loggers"

    def test_new_group_with_name(self):
        client = _make_async_logging_client()
        grp = client.management.new_group("db-loggers", name="DB Loggers")
        assert grp.name == "DB Loggers"

    def test_new_group_auto_generates_name(self):
        client = _make_async_logging_client()
        grp = client.management.new_group("db-loggers")
        assert grp.name == "Db Loggers"

    def test_new_group_with_parent_group(self):
        client = _make_async_logging_client()
        grp = client.management.new_group("child", group="parent-id")
        assert grp.group == "parent-id"


# ---------------------------------------------------------------------------
# list()
# ---------------------------------------------------------------------------


class TestAsyncList:
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_list(self, mock_list):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        mock_list.return_value = _ok_response(_make_list_parsed([resource]))

        client = _make_async_logging_client()
        result = asyncio.run(client.management.list())
        assert len(result) == 1
        assert isinstance(result[0], AsyncSmplLogger)

    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_list_empty_parsed(self, mock_list):
        mock_list.return_value = _ok_response(None)
        client = _make_async_logging_client()
        result = asyncio.run(client.management.list())
        assert result == []


# ---------------------------------------------------------------------------
# get(id) — direct lookup via get_logger
# ---------------------------------------------------------------------------


class TestAsyncGet:
    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get_by_id(self, mock_get):
        attrs = _make_logger_attrs()
        resource = _make_resource(attrs)
        mock_get.return_value = _ok_response(_make_parsed(resource))

        client = _make_async_logging_client()
        result = asyncio.run(client.management.get("sql"))
        assert isinstance(result, AsyncSmplLogger)
        assert mock_get.call_args.args[0] == "sql"

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get_not_found_404(self, mock_get):
        mock_get.return_value = _ok_response(None, HTTPStatus.NOT_FOUND)
        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.management.get("sql"))

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get_not_found_null_parsed(self, mock_get):
        mock_get.return_value = _ok_response(None)
        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.management.get("sql"))


# ---------------------------------------------------------------------------
# save() — create (id=None) and update (id set)
# ---------------------------------------------------------------------------


class TestAsyncSaveLogger:
    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    def test_save_puts_directly_when_not_created(self, mock_update):
        """PUT is the only call for a new logger — server handles upsert."""
        attrs = _make_logger_attrs(level="DEBUG")
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_async_logging_client()
        lg = client.management.new("sql", name="SQL Logger")
        assert lg.created_at is None
        asyncio.run(lg.save())

        mock_update.assert_called_once()
        assert mock_update.call_args.args[0] == "sql"

    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    def test_save_puts_with_null_level_when_not_created(self, mock_update):
        """A new logger with no level is sent as null — server upserts without a level."""
        attrs = _make_logger_attrs(level=None)
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_update.return_value = _ok_response(parsed)

        client = _make_async_logging_client()
        lg = client.management.new("app.payments", name="Payments", managed=True)
        assert lg.level is None
        assert lg.created_at is None
        asyncio.run(lg.save())

        mock_update.assert_called_once()
        body = mock_update.call_args.kwargs["body"]
        assert body.data.attributes.level is None

    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    def test_save_updates_when_id_is_set(self, mock_update):
        updated_attrs = _make_logger_attrs(level="ERROR")
        updated_resource = _make_resource(updated_attrs)
        updated_parsed = _make_parsed(updated_resource)
        mock_update.return_value = _ok_response(updated_parsed)

        client = _make_async_logging_client()
        logger = AsyncSmplLogger(
            client,
            id=_TEST_UUID,
            name="SQL Logger",
            level=LogLevel.DEBUG,
            managed=True,
            created_at="2026-01-01T00:00:00Z",
        )
        logger.level = LogLevel.ERROR
        asyncio.run(logger.save())

        mock_update.assert_called_once()
        assert logger.level == LogLevel.ERROR

    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    def test_save_null_parsed_raises_validation(self, mock_update):
        mock_update.return_value = _ok_response(None)
        client = _make_async_logging_client()
        logger = AsyncSmplLogger(
            client,
            id=_TEST_UUID,
            name="SQL Logger",
            level=LogLevel.ERROR,
            managed=True,
            created_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(SmplValidationError):
            asyncio.run(logger.save())


# ---------------------------------------------------------------------------
# delete(id) — direct delete via delete_logger
# ---------------------------------------------------------------------------


class TestAsyncDelete:
    @patch("smplkit.logging.client.delete_logger.asyncio_detailed")
    def test_delete_by_id(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        client = _make_async_logging_client()
        asyncio.run(client.management.delete("sql"))
        mock_delete.assert_called_once()
        assert mock_delete.call_args.args[0] == "sql"

    @patch("smplkit.logging.client.delete_logger.asyncio_detailed")
    def test_delete_not_found(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NOT_FOUND)
        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.management.delete("nonexistent"))


# ---------------------------------------------------------------------------
# list_groups()
# ---------------------------------------------------------------------------


class TestAsyncListGroups:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    def test_list_groups(self, mock_list):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        mock_list.return_value = _ok_response(_make_list_parsed([resource]))

        client = _make_async_logging_client()
        result = asyncio.run(client.management.list_groups())
        assert len(result) == 1
        assert isinstance(result[0], AsyncSmplLogGroup)

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    def test_list_groups_empty_parsed(self, mock_list):
        mock_list.return_value = _ok_response(None)
        client = _make_async_logging_client()
        result = asyncio.run(client.management.list_groups())
        assert result == []


# ---------------------------------------------------------------------------
# get_group(id) — direct lookup via get_log_group
# ---------------------------------------------------------------------------


class TestAsyncGetGroup:
    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group_by_id(self, mock_get):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        mock_get.return_value = _ok_response(_make_parsed(resource))

        client = _make_async_logging_client()
        result = asyncio.run(client.management.get_group("db-loggers"))
        assert isinstance(result, AsyncSmplLogGroup)
        assert mock_get.call_args.args[0] == "db-loggers"

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group_not_found_404(self, mock_get):
        mock_get.return_value = _ok_response(None, HTTPStatus.NOT_FOUND)

        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.management.get_group("db-loggers"))

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group_not_found_null_parsed(self, mock_get):
        mock_get.return_value = _ok_response(None)
        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.management.get_group("db-loggers"))


# ---------------------------------------------------------------------------
# Group save() — create and update
# ---------------------------------------------------------------------------


class TestAsyncSaveGroup:
    @patch("smplkit.logging.client.create_log_group.asyncio_detailed")
    def test_save_creates_when_id_is_none(self, mock_create):
        attrs = _make_group_attrs()
        resource = _make_resource(attrs)
        parsed = _make_parsed(resource)
        mock_create.return_value = _ok_response(parsed, HTTPStatus.CREATED)

        client = _make_async_logging_client()
        grp = client.management.new_group("db-loggers", name="DB Loggers")
        asyncio.run(grp.save())

        mock_create.assert_called_once()
        assert grp.id == _TEST_UUID

    @patch("smplkit.logging.client.update_log_group.asyncio_detailed")
    def test_save_updates_when_id_is_set(self, mock_update):
        updated_attrs = _make_group_attrs(level="ERROR")
        updated_resource = _make_resource(updated_attrs)
        updated_parsed = _make_parsed(updated_resource)
        mock_update.return_value = _ok_response(updated_parsed)

        client = _make_async_logging_client()
        group = AsyncSmplLogGroup(
            client,
            id=_TEST_UUID,
            name="DB Loggers",
            level=LogLevel.WARN,
            created_at="2026-01-01T00:00:00Z",
        )
        group.level = LogLevel.ERROR
        asyncio.run(group.save())

        mock_update.assert_called_once()
        assert group.level == LogLevel.ERROR

    @patch("smplkit.logging.client.update_log_group.asyncio_detailed")
    def test_save_null_parsed_raises_validation(self, mock_update):
        mock_update.return_value = _ok_response(None)
        client = _make_async_logging_client()
        group = AsyncSmplLogGroup(
            client,
            id=_TEST_UUID,
            name="DB Loggers",
            level=LogLevel.ERROR,
            created_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(SmplValidationError):
            asyncio.run(group.save())


# ---------------------------------------------------------------------------
# delete_group(id) — direct delete via delete_log_group
# ---------------------------------------------------------------------------


class TestAsyncDeleteGroup:
    @patch("smplkit.logging.client.delete_log_group.asyncio_detailed")
    def test_delete_group_by_id(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        client = _make_async_logging_client()
        asyncio.run(client.management.delete_group("db-loggers"))
        mock_delete.assert_called_once()
        assert mock_delete.call_args.args[0] == "db-loggers"

    @patch("smplkit.logging.client.delete_log_group.asyncio_detailed")
    def test_delete_group_not_found(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NOT_FOUND)
        client = _make_async_logging_client()
        with pytest.raises(SmplNotFoundError):
            asyncio.run(client.management.delete_group("nonexistent"))


# ---------------------------------------------------------------------------
# Async model convenience methods
# ---------------------------------------------------------------------------


class TestAsyncLoggerConvenienceMethods:
    def test_setLevel(self):
        lg = AsyncSmplLogger(None, id="sql", name="SQL Logger")
        lg.setLevel(LogLevel.ERROR)
        assert lg.level == "ERROR"

    def test_clearLevel(self):
        lg = AsyncSmplLogger(None, id="sql", name="SQL Logger", level="DEBUG")
        lg.clearLevel()
        assert lg.level is None

    def test_setEnvironmentLevel(self):
        lg = AsyncSmplLogger(None, id="sql", name="SQL Logger")
        lg.setEnvironmentLevel("prod", LogLevel.WARN)
        assert lg.environments["prod"] == {"level": "WARN"}

    def test_clearEnvironmentLevel(self):
        lg = AsyncSmplLogger(None, id="sql", name="SQL Logger", environments={"prod": {"level": "WARN"}})
        lg.clearEnvironmentLevel("prod")
        assert "prod" not in lg.environments

    def test_clearEnvironmentLevel_missing_key(self):
        lg = AsyncSmplLogger(None, id="sql", name="SQL Logger")
        lg.clearEnvironmentLevel("nonexistent")

    def test_clearAllEnvironmentLevels(self):
        lg = AsyncSmplLogger(
            None, id="sql", name="SQL Logger", environments={"prod": {"level": "WARN"}, "dev": {"level": "DEBUG"}}
        )
        lg.clearAllEnvironmentLevels()
        assert lg.environments == {}


class TestAsyncLogGroupConvenienceMethods:
    def test_setLevel(self):
        grp = AsyncSmplLogGroup(None, id="db", name="DB")
        grp.setLevel(LogLevel.ERROR)
        assert grp.level == "ERROR"

    def test_clearLevel(self):
        grp = AsyncSmplLogGroup(None, id="db", name="DB", level="WARN")
        grp.clearLevel()
        assert grp.level is None

    def test_setEnvironmentLevel(self):
        grp = AsyncSmplLogGroup(None, id="db", name="DB")
        grp.setEnvironmentLevel("staging", LogLevel.DEBUG)
        assert grp.environments["staging"] == {"level": "DEBUG"}

    def test_clearEnvironmentLevel(self):
        grp = AsyncSmplLogGroup(None, id="db", name="DB", environments={"staging": {"level": "DEBUG"}})
        grp.clearEnvironmentLevel("staging")
        assert "staging" not in grp.environments

    def test_clearEnvironmentLevel_missing_key(self):
        grp = AsyncSmplLogGroup(None, id="db", name="DB")
        grp.clearEnvironmentLevel("nonexistent")

    def test_clearAllEnvironmentLevels(self):
        grp = AsyncSmplLogGroup(None, id="db", name="DB", environments={"a": {}, "b": {}})
        grp.clearAllEnvironmentLevels()
        assert grp.environments == {}


# ---------------------------------------------------------------------------
# start() — async wrapper for _connect_internal()
# ---------------------------------------------------------------------------


class TestAsyncStart:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_start_connects(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = []
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        asyncio.run(client.start())
        assert client._connected is True
        client._close()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_start_is_idempotent(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = []
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        asyncio.run(client.start())
        asyncio.run(client.start())
        mock_auto_load.assert_called_once()
        client._close()


# ---------------------------------------------------------------------------
# on_change — dual-mode decorator
# ---------------------------------------------------------------------------


class TestAsyncOnChange:
    def test_bare_decorator_global(self):
        client = _make_async_logging_client()

        @client.on_change
        def handler():
            pass

        assert handler in client._global_listeners

    def test_key_scoped_decorator(self):
        client = _make_async_logging_client()

        @client.on_change("sqlalchemy.engine")
        def handler():
            pass

        assert handler in client._key_listeners["sqlalchemy.engine"]

    def test_parens_no_args_global(self):
        client = _make_async_logging_client()

        @client.on_change()
        def handler():
            pass

        assert handler in client._global_listeners

    def test_returns_original_function(self):
        client = _make_async_logging_client()

        @client.on_change("key")
        def my_fn():
            pass

        assert my_fn.__name__ == "my_fn"


# ---------------------------------------------------------------------------
# Connect flow
# ---------------------------------------------------------------------------


class TestAsyncConnectFlow:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_full_flow(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = [("root", 30, 30), ("myapp.db", 10, 10)]
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        asyncio.run(client._connect_internal())

        assert client._connected is True
        mock_adapter.discover.assert_called_once()
        mock_adapter.install_hook.assert_called_once()
        mock_bulk.assert_called_once()
        client._close()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_with_service(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = [("root", 30, 30)]
        mock_auto_load.return_value = [mock_adapter]
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
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_fetch_failure_is_resilient(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = []
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.side_effect = Exception("network error")

        client = _make_async_logging_client()
        asyncio.run(client._connect_internal())
        assert client._connected is True
        client._close()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_idempotent(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = []
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        asyncio.run(client._connect_internal())
        asyncio.run(client._connect_internal())
        mock_auto_load.assert_called_once()
        client._close()


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestAsyncRefresh:
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

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_refresh_without_connect_works(self, mock_loggers, mock_groups):
        """refresh() no longer raises SmplNotConnectedError."""
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        assert client._connected is False
        asyncio.run(client.refresh())
        mock_loggers.assert_called_once()


# ---------------------------------------------------------------------------
# Bulk flush
# ---------------------------------------------------------------------------


class TestAsyncBulkFlush:
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    def test_async_flush(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", "INFO", None, None)
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
        client._buffer.add("com.test", "INFO", "INFO", None, None)
        asyncio.run(client._flush_bulk_async())

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_sync_flush_on_timer(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", "INFO", None, None)
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
        client._buffer.add("com.test", "INFO", "INFO", None, None)
        client._flush_bulk_sync()

    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    def test_async_flush_logs_warning_on_http_error(self, mock_bulk, caplog):
        import logging as stdlib_logging

        mock_bulk.return_value = _ok_response(status=HTTPStatus.BAD_REQUEST)
        mock_bulk.return_value.content = b'{"errors":[{"detail":"bad"}]}'
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", "INFO", None, None)
        with caplog.at_level(stdlib_logging.WARNING, logger="smplkit"):
            asyncio.run(client._flush_bulk_async())
        assert len(caplog.records) == 1
        assert "400" in caplog.records[0].message
        assert caplog.records[0].levelno == stdlib_logging.WARNING

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_sync_flush_logs_warning_on_http_error(self, mock_bulk, caplog):
        import logging as stdlib_logging

        mock_bulk.return_value = _ok_response(status=HTTPStatus.BAD_REQUEST)
        mock_bulk.return_value.content = b'{"errors":[{"detail":"bad"}]}'
        client = _make_async_logging_client()
        client._buffer.add("com.test", "INFO", "INFO", None, None)
        with caplog.at_level(stdlib_logging.WARNING, logger="smplkit"):
            client._flush_bulk_sync()
        assert len(caplog.records) == 1
        assert "400" in caplog.records[0].message
        assert caplog.records[0].levelno == stdlib_logging.WARNING


# ---------------------------------------------------------------------------
# On new logger callback
# ---------------------------------------------------------------------------


class TestAsyncOnNewLogger:
    def test_callback_adds_to_buffer(self):
        client = _make_async_logging_client()
        client._on_new_logger("my.new.logger", 20, 20)
        assert client._buffer.pending_count == 1
        assert "my.new.logger" in client._name_map

    def test_callback_applies_level_when_connected(self):
        client = _make_async_logging_client()
        client._connected = True
        test_name = "test.async.on_new.managed_xyz"
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


# ---------------------------------------------------------------------------
# Level application
# ---------------------------------------------------------------------------


class TestAsyncLevelApplication:
    def test_apply_levels_managed(self):
        client = _make_async_logging_client()
        test_name = "test.async.apply.managed_111"
        mock_adapter = MagicMock()
        client._adapters = [mock_adapter]
        client._name_map[test_name] = test_name
        client._loggers_cache = {
            test_name: {
                "level": "WARN",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._apply_levels()
        mock_adapter.apply_level.assert_called_once_with(test_name, 30)

    def test_apply_levels_unmanaged_skipped(self):
        client = _make_async_logging_client()
        test_name = "test.async.apply.unmanaged_222"
        mock_adapter = MagicMock()
        client._adapters = [mock_adapter]
        client._name_map[test_name] = test_name
        client._loggers_cache = {
            test_name: {
                "level": "ERROR",
                "group": None,
                "managed": False,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._apply_levels()
        mock_adapter.apply_level.assert_not_called()

    def test_apply_levels_not_in_runtime_skipped(self):
        client = _make_async_logging_client()
        client._loggers_cache = {
            "some.remote": {
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        client._groups_cache = {}
        client._apply_levels()  # Should not raise


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------


class TestAsyncClose:
    def test_close_uninstalls_adapters(self):
        client = _make_async_logging_client()
        adapter = MagicMock()
        client._adapters = [adapter]
        client._close()
        adapter.uninstall_hook.assert_called_once()

    def test_close_cancels_timer(self):
        client = _make_async_logging_client()
        timer = MagicMock()
        client._flush_timer = timer
        client._close()
        timer.cancel.assert_called_once()
        assert client._flush_timer is None


# ---------------------------------------------------------------------------
# Schedule flush
# ---------------------------------------------------------------------------


class TestAsyncScheduleFlush:
    def test_schedule_creates_timer(self):
        client = _make_async_logging_client()
        client._schedule_flush()
        assert client._flush_timer is not None
        client._flush_timer.cancel()


# ---------------------------------------------------------------------------
# Fetch and apply
# ---------------------------------------------------------------------------


class TestAsyncFetchAndApply:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_fetches_and_caches(self, mock_loggers, mock_groups):
        logger_attrs = _make_logger_attrs(managed=True)
        logger_resource = _make_resource(logger_attrs, id="com.test")
        mock_loggers.return_value = _ok_response(_make_list_parsed([logger_resource]))

        group_attrs = _make_group_attrs()
        group_resource = _make_resource(group_attrs, id="grp-1")
        mock_groups.return_value = _ok_response(_make_list_parsed([group_resource]))

        client = _make_async_logging_client()
        asyncio.run(client._fetch_and_apply())

        assert "com.test" in client._loggers_cache
        assert "grp-1" in client._groups_cache

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_group_parent_id_stored_as_group_key(self, mock_loggers, mock_groups):
        """groups_cache['group'] must come from parent_id, not a nonexistent 'group' attr."""
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))

        group_attrs = _make_group_attrs(parent_id="parent-grp-id")
        group_resource = _make_resource(group_attrs, id="child-grp")
        mock_groups.return_value = _ok_response(_make_list_parsed([group_resource]))

        client = _make_async_logging_client()
        asyncio.run(client._fetch_and_apply())

        assert client._groups_cache["child-grp"]["group"] == "parent-grp-id"


# ---------------------------------------------------------------------------
# WebSocket event handling
# ---------------------------------------------------------------------------


class TestWebSocketEventHandling:
    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed")
    @patch("smplkit.logging.client._auto_load_adapters")
    def test_connect_registers_ws_handlers(self, mock_auto_load, mock_bulk, mock_loggers, mock_groups):
        """_connect_internal registers handlers for all five logger events."""
        mock_adapter = MagicMock()
        mock_adapter.discover.return_value = []
        mock_auto_load.return_value = [mock_adapter]
        mock_bulk.return_value = _ok_response()
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws

        asyncio.run(client._connect_internal())

        assert mock_ws.on.call_count == 5
        registered_events = {call[0][0] for call in mock_ws.on.call_args_list}
        assert registered_events == {
            "logger_changed",
            "logger_deleted",
            "group_changed",
            "group_deleted",
            "loggers_changed",
        }
        client._close()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_handle_loggers_changed_triggers_refetch_in_thread(self, mock_loggers, mock_groups):
        """_handle_loggers_changed spawns a thread that runs _fetch_and_apply."""
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        client._handle_loggers_changed({})

        # Give the daemon thread time to run
        import time

        time.sleep(0.2)

        mock_loggers.assert_called_once()
        mock_groups.assert_called_once()

    def test_close_deregisters_ws_handlers(self):
        """_close calls off() for all five events on the ws manager."""
        client = _make_async_logging_client()
        mock_ws = MagicMock()
        client._ws_manager = mock_ws

        client._close()

        assert mock_ws.off.call_count == 5
        deregistered_events = {call[0][0] for call in mock_ws.off.call_args_list}
        assert deregistered_events == {
            "logger_changed",
            "logger_deleted",
            "group_changed",
            "group_deleted",
            "loggers_changed",
        }
        assert client._ws_manager is None

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_handle_loggers_changed_swallows_fetch_errors(self, mock_loggers, mock_groups):
        """_handle_loggers_changed catches exceptions from the async _fetch_and_apply thread."""
        mock_loggers.side_effect = RuntimeError("network failure")

        client = _make_async_logging_client()
        # Should not raise; the error is caught inside the daemon thread
        client._handle_loggers_changed({})

        import time

        time.sleep(0.2)  # let thread finish

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_handle_loggers_changed_successive_events_no_event_loop_error(self, mock_loggers, mock_groups):
        """Successive loggers_changed events must not raise 'RuntimeError: Event loop is closed'.

        Regression test: previously _fetch_and_apply reused self._logging_http
        (a shared AuthenticatedClient) across different temporary event loops.
        The httpx AsyncClient caches asyncio transports bound to the first loop;
        when that loop is closed and a second loop reuses the same client,
        cleanup callbacks fire against the now-closed loop.
        """
        import time

        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()

        client._handle_loggers_changed({})
        client._handle_loggers_changed({})

        time.sleep(0.4)  # let both daemon threads finish

        # Both events must have triggered a full refresh cycle.
        assert mock_loggers.call_count == 2
        assert mock_groups.call_count == 2

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    @patch("smplkit.logging.client.AuthenticatedClient")
    def test_handle_loggers_changed_closes_fresh_http_client(self, mock_ac_cls, mock_loggers, mock_groups):
        """The underlying httpx AsyncClient of the fresh client is closed after loggers_changed refresh."""
        import time

        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        # Provide a mock http instance with a non-None _async_client so that the
        # `if ac is not None: await ac.aclose()` branch is exercised.
        mock_async_client = AsyncMock()
        mock_http_instance = MagicMock()
        mock_http_instance._async_client = mock_async_client
        mock_ac_cls.return_value = mock_http_instance

        # _make_async_logging_client() opens its own nested patch for AuthenticatedClient
        # (to set up _logging_http), temporarily overriding mock_ac_cls.  After it
        # exits the constructor, mock_ac_cls is restored and is what _handle_loggers_changed
        # will see when it calls AuthenticatedClient(...).
        client = _make_async_logging_client()
        client._handle_loggers_changed({})

        time.sleep(0.3)  # let the daemon thread finish

        mock_async_client.aclose.assert_called_once()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_handle_loggers_changed_uses_fresh_http_client(self, mock_loggers, mock_groups):
        """loggers_changed refresh must use a fresh AuthenticatedClient, not self._logging_http."""
        import time

        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.return_value = _ok_response(_make_list_parsed([]))

        client = _make_async_logging_client()
        client._handle_loggers_changed({})

        time.sleep(0.2)

        mock_loggers.assert_called_once()
        # The client passed to the API call must NOT be self._logging_http;
        # it must be a fresh AuthenticatedClient scoped to the thread's event loop.
        call_client = mock_loggers.call_args.kwargs.get("client") or mock_loggers.call_args.args[0]
        assert call_client is not client._logging_http

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_handle_logger_changed_spawns_thread_and_fires(self, mock_get):
        """_handle_logger_changed spawns a thread that fetches a single logger and fires listeners."""
        import time
        from smplkit.logging.client import LoggerResponse, LoggerResource, GenLogger
        from smplkit._generated.logging.types import UNSET

        attrs = GenLogger(name="sqlalchemy.engine", level="INFO", group=UNSET, managed=True, environments=UNSET)
        resource = LoggerResource(attributes=attrs, id="sqlalchemy.engine", type_="logger")
        parsed = LoggerResponse(data=resource)
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.content = b""
        resp.parsed = parsed
        mock_get.return_value = resp

        client = _make_async_logging_client()
        client._loggers_cache["sqlalchemy.engine"] = {
            "level": "DEBUG",
            "group": None,
            "managed": True,
            "environments": {},
        }
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_logger_changed({"id": "sqlalchemy.engine"})
        time.sleep(0.3)
        mock_get.assert_called_once()
        listener.assert_called_once()

    def test_handle_logger_deleted_spawns_thread_and_fires(self):
        """_handle_logger_deleted spawns a thread and fires deleted listener."""
        import time

        client = _make_async_logging_client()
        client._loggers_cache["sqlalchemy.engine"] = {
            "level": "DEBUG",
            "group": None,
            "managed": True,
            "environments": {},
        }
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_logger_deleted({"id": "sqlalchemy.engine"})
        time.sleep(0.3)
        assert "sqlalchemy.engine" not in client._loggers_cache
        listener.assert_called_once()
        event = listener.call_args[0][0]
        assert event.deleted is True

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_handle_group_changed_spawns_thread_and_fires(self, mock_get):
        """_handle_group_changed spawns a thread that fetches a single group and fires listeners."""
        import time
        from smplkit.logging.client import LogGroupResponse, LogGroupResource, GenLogGroup
        from smplkit._generated.logging.types import UNSET

        attrs = GenLogGroup(name="db-loggers", level="ERROR", parent_id=UNSET, environments=UNSET)
        resource = LogGroupResource(attributes=attrs, id="db-loggers", type_="log_group")
        parsed = LogGroupResponse(data=resource)
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.content = b""
        resp.parsed = parsed
        mock_get.return_value = resp

        client = _make_async_logging_client()
        client._groups_cache["db-loggers"] = {"level": "WARN", "group": None, "environments": {}}
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_group_changed({"id": "db-loggers"})
        time.sleep(0.3)
        mock_get.assert_called_once()
        listener.assert_called_once()

    def test_handle_group_deleted_spawns_thread_and_fires(self):
        """_handle_group_deleted spawns a thread and fires deleted listener."""
        import time

        client = _make_async_logging_client()
        client._groups_cache["db-loggers"] = {"level": "WARN", "group": None, "environments": {}}
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_group_deleted({"id": "db-loggers"})
        time.sleep(0.3)
        assert "db-loggers" not in client._groups_cache
        listener.assert_called_once()
        event = listener.call_args[0][0]
        assert event.deleted is True

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_async_fire_change_listeners_global_exception_swallowed(self, mock_get):
        """Async _fire_change_listeners swallows exceptions from global listeners."""
        import time
        from smplkit.logging.client import LoggerResponse, LoggerResource, GenLogger
        from smplkit._generated.logging.types import UNSET

        attrs = GenLogger(name="sqlalchemy.engine", level="INFO", group=UNSET, managed=True, environments=UNSET)
        resource = LoggerResource(attributes=attrs, id="sqlalchemy.engine", type_="logger")
        parsed = LoggerResponse(data=resource)
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.content = b""
        resp.parsed = parsed
        mock_get.return_value = resp

        client = _make_async_logging_client()
        client._loggers_cache["sqlalchemy.engine"] = {
            "level": "DEBUG",
            "group": None,
            "managed": True,
            "environments": {},
        }
        bad = MagicMock(side_effect=RuntimeError("boom"))
        good = MagicMock()
        client._global_listeners.extend([bad, good])
        client._handle_logger_changed({"id": "sqlalchemy.engine"})
        time.sleep(0.3)
        good.assert_called_once()

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_async_fire_change_listeners_key_exception_swallowed(self, mock_get):
        """Async _fire_change_listeners swallows exceptions from per-key listeners."""
        import time
        from smplkit.logging.client import LoggerResponse, LoggerResource, GenLogger
        from smplkit._generated.logging.types import UNSET

        attrs = GenLogger(name="sqlalchemy.engine", level="INFO", group=UNSET, managed=True, environments=UNSET)
        resource = LoggerResource(attributes=attrs, id="sqlalchemy.engine", type_="logger")
        parsed = LoggerResponse(data=resource)
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.content = b""
        resp.parsed = parsed
        mock_get.return_value = resp

        client = _make_async_logging_client()
        client._loggers_cache["sqlalchemy.engine"] = {
            "level": "DEBUG",
            "group": None,
            "managed": True,
            "environments": {},
        }
        bad = MagicMock(side_effect=RuntimeError("boom"))
        good = MagicMock()
        client._key_listeners["sqlalchemy.engine"] = [bad, good]
        client._handle_logger_changed({"id": "sqlalchemy.engine"})
        time.sleep(0.3)
        good.assert_called_once()

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_handle_logger_changed_fetch_error_swallowed(self, mock_get):
        """_fetch_logger_and_apply catches exceptions from asyncio_detailed and returns."""
        import time

        mock_get.side_effect = RuntimeError("fetch failed")
        client = _make_async_logging_client()
        client._handle_logger_changed({"id": "sqlalchemy.engine"})
        time.sleep(0.3)  # should not raise

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_handle_group_changed_fetch_error_swallowed(self, mock_get):
        """_fetch_group_and_apply catches exceptions from asyncio_detailed and returns."""
        import time

        mock_get.side_effect = RuntimeError("fetch failed")
        client = _make_async_logging_client()
        client._handle_group_changed({"id": "db-loggers"})
        time.sleep(0.3)  # should not raise

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    @patch("smplkit.logging.client.AuthenticatedClient")
    def test_handle_logger_changed_closes_fresh_http_client(self, mock_ac_cls, mock_get):
        """_run_ws_handler closes the fresh http client's _async_client after fetch."""
        import time

        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.content = b""
        resp.parsed = None
        mock_get.return_value = resp

        mock_async_client = AsyncMock()
        mock_http_instance = MagicMock()
        mock_http_instance._async_client = mock_async_client
        mock_ac_cls.return_value = mock_http_instance

        client = _make_async_logging_client()
        client._handle_logger_changed({"id": "sqlalchemy.engine"})
        time.sleep(0.3)
        mock_async_client.aclose.assert_called_once()

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_handle_logger_changed_apply_levels_error_swallowed(self, mock_get):
        """_run_ws_handler swallows exceptions from _apply_levels."""
        import time
        from smplkit.logging.client import LoggerResponse, LoggerResource, GenLogger
        from smplkit._generated.logging.types import UNSET

        attrs = GenLogger(name="sqlalchemy.engine", level="INFO", group=UNSET, managed=True, environments=UNSET)
        resource = LoggerResource(attributes=attrs, id="sqlalchemy.engine", type_="logger")
        parsed = LoggerResponse(data=resource)
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.content = b""
        resp.parsed = parsed
        mock_get.return_value = resp

        client = _make_async_logging_client()
        with patch.object(client, "_apply_levels", side_effect=RuntimeError("apply failed")):
            client._handle_logger_changed({"id": "sqlalchemy.engine"})
            time.sleep(0.3)  # should not raise

    def test_handle_logger_deleted_apply_error_swallowed(self):
        """logger_deleted thread swallows exceptions from _apply_levels."""
        import time

        client = _make_async_logging_client()
        client._loggers_cache["sqlalchemy.engine"] = {"level": "DEBUG"}
        with patch.object(client, "_apply_levels", side_effect=RuntimeError("apply failed")):
            client._handle_logger_deleted({"id": "sqlalchemy.engine"})
            time.sleep(0.3)  # should not raise

    def test_handle_group_deleted_apply_error_swallowed(self):
        """group_deleted thread swallows exceptions from _apply_levels."""
        import time

        client = _make_async_logging_client()
        client._groups_cache["db-loggers"] = {"level": "WARN"}
        with patch.object(client, "_apply_levels", side_effect=RuntimeError("apply failed")):
            client._handle_group_deleted({"id": "db-loggers"})
            time.sleep(0.3)  # should not raise


# ---------------------------------------------------------------------------
# AsyncLoggingManagementClient.register_sources
# ---------------------------------------------------------------------------


class TestAsyncRegisterSources:
    def test_register_sources_basic(self):
        from smplkit.logging._sources import LoggerSource

        async def _run():
            mock_coro = AsyncMock(return_value=MagicMock(status_code=200, content=b"{}"))
            with patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed", mock_coro):
                client = _make_async_logging_client()
                await client.management.register_sources(
                    [
                        LoggerSource(
                            name="sqlalchemy.engine",
                            service="api",
                            environment="production",
                            resolved_level=LogLevel.WARN,
                        ),
                    ]
                )
                mock_coro.assert_called_once()
                _, kwargs = mock_coro.call_args
                assert kwargs["body"].loggers[0].service == "api"

        asyncio.run(_run())

    def test_register_sources_with_level(self):
        from smplkit.logging._sources import LoggerSource

        async def _run():
            mock_coro = AsyncMock(return_value=MagicMock(status_code=200, content=b"{}"))
            with patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed", mock_coro):
                client = _make_async_logging_client()
                await client.management.register_sources(
                    [
                        LoggerSource(
                            name="httpx",
                            service="svc",
                            environment="staging",
                            resolved_level=LogLevel.INFO,
                            level=LogLevel.DEBUG,
                        ),
                    ]
                )
                _, kwargs = mock_coro.call_args
                assert kwargs["body"].loggers[0].level == "DEBUG"

        asyncio.run(_run())

    def test_register_sources_empty_list_skips_call(self):
        async def _run():
            mock_coro = AsyncMock(return_value=MagicMock(status_code=200, content=b"{}"))
            with patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed", mock_coro):
                client = _make_async_logging_client()
                await client.management.register_sources([])
                mock_coro.assert_not_called()

        asyncio.run(_run())

    def test_register_sources_generic_error_reraises(self):
        from smplkit.logging._sources import LoggerSource

        async def _run():
            mock_coro = AsyncMock(side_effect=RuntimeError("unexpected"))
            with patch("smplkit.logging.client.bulk_register_loggers.asyncio_detailed", mock_coro):
                client = _make_async_logging_client()
                with pytest.raises(RuntimeError):
                    await client.management.register_sources(
                        [
                            LoggerSource("app", service="svc", environment="prod", resolved_level=LogLevel.INFO),
                        ]
                    )

        asyncio.run(_run())
