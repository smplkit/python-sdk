"""Tests targeting specific uncovered lines in logging/client.py."""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import pytest

from smplkit._errors import SmplConnectionError
from smplkit.logging.client import (
    AsyncLoggingClient,
    AsyncSmplLogGroup,
    AsyncSmplLogger,
    LoggingClient,
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


def _make_group_attrs(*, key="db", name="DB", level="WARN", group=None):
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


def _ok_response(parsed=None, status=HTTPStatus.OK):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b""
    resp.parsed = parsed
    return resp


def _make_sync_client(**kwargs):
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = kwargs.get("service", None)
    with patch("smplkit.logging.client.AuthenticatedClient"):
        return LoggingClient(parent)


def _make_async_client(**kwargs):
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = kwargs.get("service", None)
    with patch("smplkit.logging.client.AuthenticatedClient"):
        return AsyncLoggingClient(parent)


# ---------------------------------------------------------------------------
# Bare `raise` after _maybe_reraise_network_error (non-httpx exceptions)
# ---------------------------------------------------------------------------


class TestSyncBareRaise:
    """Cover the `raise` line after _maybe_reraise_network_error for non-httpx errors."""

    @patch("smplkit.logging.client.create_logger.sync_detailed")
    def test_create_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.create("sql", name="SQL")

    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_list_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.list()

    @patch("smplkit.logging.client.get_logger.sync_detailed")
    def test_get_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.get(_TEST_UUID)

    @patch("smplkit.logging.client.update_logger.sync_detailed")
    def test_save_logger_unknown_error(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        lg = SmplLogger(client, id=_TEST_UUID, key="sql", name="SQL Logger")
        with pytest.raises(RuntimeError, match="boom"):
            client._save_logger(lg)

    @patch("smplkit.logging.client.delete_logger.sync_detailed")
    def test_delete_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.delete(_TEST_UUID)

    @patch("smplkit.logging.client.create_log_group.sync_detailed")
    def test_create_group_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.create_group("db", name="DB")

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    def test_list_groups_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.list_groups()

    @patch("smplkit.logging.client.get_log_group.sync_detailed")
    def test_get_group_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.get_group(_TEST_UUID)

    @patch("smplkit.logging.client.update_log_group.sync_detailed")
    def test_save_group_unknown_error(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        grp = SmplLogGroup(client, id=_TEST_UUID, key="db", name="DB")
        with pytest.raises(RuntimeError, match="boom"):
            client._save_group(grp)

    @patch("smplkit.logging.client.delete_log_group.sync_detailed")
    def test_delete_group_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client.delete_group(_TEST_UUID)


class TestAsyncBareRaise:
    """Cover the bare `raise` after _maybe_reraise_network_error for async methods."""

    @patch("smplkit.logging.client.create_logger.asyncio_detailed")
    def test_create_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.create("sql", name="SQL"))

    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_list_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.list())

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.get(_TEST_UUID))

    @patch("smplkit.logging.client.delete_logger.asyncio_detailed")
    def test_delete_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.delete(_TEST_UUID))

    @patch("smplkit.logging.client.create_log_group.asyncio_detailed")
    def test_create_group_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.create_group("db", name="DB"))

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    def test_list_groups_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.list_groups())

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.get_group(_TEST_UUID))

    @patch("smplkit.logging.client.delete_log_group.asyncio_detailed")
    def test_delete_group_unknown_error(self, mock):
        mock.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client.delete_group(_TEST_UUID))

    @patch("smplkit.logging.client.update_logger.asyncio_detailed")
    def test_save_logger_unknown_error(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        client = _make_async_client()
        lg = AsyncSmplLogger(client, id=_TEST_UUID, key="sql", name="SQL Logger")
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client._save_logger(lg))

    @patch("smplkit.logging.client.update_log_group.asyncio_detailed")
    def test_save_group_unknown_error(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        client = _make_async_client()
        grp = AsyncSmplLogGroup(client, id=_TEST_UUID, key="db", name="DB")
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client._save_group(grp))


# ---------------------------------------------------------------------------
# Timer _tick() coverage
# ---------------------------------------------------------------------------


class TestTickCallback:
    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_sync_tick(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_sync_client()
        client._connected = True
        client._buffer.add("a", "INFO", None)

        # Call _schedule_flush, then immediately fire the tick
        client._schedule_flush()
        timer = client._flush_timer
        timer.cancel()
        # Manually invoke the tick callback
        timer.function()
        # Cleanup the timer it scheduled
        if client._flush_timer is not None:
            client._flush_timer.cancel()

    @patch("smplkit.logging.client.bulk_register_loggers.sync_detailed")
    def test_async_tick(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_async_client()
        client._connected = True
        client._buffer.add("a", "INFO", None)

        client._schedule_flush()
        timer = client._flush_timer
        timer.cancel()
        timer.function()
        if client._flush_timer is not None:
            client._flush_timer.cancel()


# ---------------------------------------------------------------------------
# Async network error paths (httpx exceptions)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# _fetch_and_apply: list_log_groups failure
# ---------------------------------------------------------------------------


def _make_list_parsed(resources):
    parsed = MagicMock()
    parsed.data = resources
    return parsed


class TestFetchAndApplyGroupFailure:
    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_sync_groups_fetch_network_error(self, mock_loggers, mock_groups):
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.side_effect = httpx.ConnectError("refused")
        client = _make_sync_client()
        with pytest.raises(SmplConnectionError):
            client._fetch_and_apply()

    @patch("smplkit.logging.client.list_log_groups.sync_detailed")
    @patch("smplkit.logging.client.list_loggers.sync_detailed")
    def test_sync_groups_fetch_unknown_error(self, mock_loggers, mock_groups):
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.side_effect = RuntimeError("boom")
        client = _make_sync_client()
        with pytest.raises(RuntimeError, match="boom"):
            client._fetch_and_apply()

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_async_groups_fetch_network_error(self, mock_loggers, mock_groups):
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client._fetch_and_apply())

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_async_groups_fetch_unknown_error(self, mock_loggers, mock_groups):
        mock_loggers.return_value = _ok_response(_make_list_parsed([]))
        mock_groups.side_effect = RuntimeError("boom")
        client = _make_async_client()
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(client._fetch_and_apply())


class TestAsyncNetworkErrors:
    @patch("smplkit.logging.client.create_logger.asyncio_detailed")
    def test_create_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.create("sql", name="SQL"))

    @patch("smplkit.logging.client.list_loggers.asyncio_detailed")
    def test_list_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.list())

    @patch("smplkit.logging.client.get_logger.asyncio_detailed")
    def test_get_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.get(_TEST_UUID))

    @patch("smplkit.logging.client.delete_logger.asyncio_detailed")
    def test_delete_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.delete(_TEST_UUID))

    @patch("smplkit.logging.client.create_log_group.asyncio_detailed")
    def test_create_group_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.create_group("db", name="DB"))

    @patch("smplkit.logging.client.list_log_groups.asyncio_detailed")
    def test_list_groups_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.list_groups())

    @patch("smplkit.logging.client.get_log_group.asyncio_detailed")
    def test_get_group_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.get_group(_TEST_UUID))

    @patch("smplkit.logging.client.delete_log_group.asyncio_detailed")
    def test_delete_group_network_error(self, mock):
        mock.side_effect = httpx.ConnectError("refused")
        client = _make_async_client()
        with pytest.raises(SmplConnectionError):
            asyncio.run(client.delete_group(_TEST_UUID))
