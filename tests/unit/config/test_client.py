"""Tests for ConfigClient and AsyncConfigClient."""

import asyncio
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import pytest

from smplkit._errors import (
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.config.client import AsyncConfigClient

_TEST_UUID = "5a0c6be1-0000-0000-0000-000000000001"
_TEST_UUID_2 = "5a0c6be1-0000-0000-0000-000000000002"


class TestConfigClient:
    def test_get_requires_key_or_id(self):
        client = SmplClient(api_key="sk_test")
        with pytest.raises(ValueError, match="Exactly one"):
            client.config.get()

    def test_get_rejects_both_key_and_id(self):
        client = SmplClient(api_key="sk_test")
        with pytest.raises(ValueError, match="Exactly one"):
            client.config.get(key="k", id="i")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_by_id(self, mock_get):
        # Build a mock response matching the generated client pattern
        mock_attrs = MagicMock()
        mock_attrs.name = "Test"
        mock_attrs.key = "test"
        mock_attrs.description = "desc"
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = mock_resource

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_get.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        cfg = client.config.get(id=_TEST_UUID)
        assert cfg.id == _TEST_UUID
        assert cfg.name == "Test"

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_get_by_key_not_found(self, mock_list):
        mock_parsed = MagicMock()
        mock_parsed.data = []

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_list.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplNotFoundError):
            client.config.get(key="nonexistent")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_by_id_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NOT_FOUND
        mock_response.content = b"Not Found"
        mock_response.parsed = None

        mock_get.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplNotFoundError):
            client.config.get(id=_TEST_UUID_2)

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create(self, mock_create):
        mock_attrs = MagicMock()
        mock_attrs.name = "New Config"
        mock_attrs.key = "new_config"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = mock_resource

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CREATED
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_create.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        cfg = client.config.create(name="New Config", key="new_config")
        assert cfg.id == _TEST_UUID
        assert cfg.name == "New Config"

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list(self, mock_list):
        mock_attrs = MagicMock()
        mock_attrs.name = "Config 1"
        mock_attrs.key = "c1"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_list.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        configs = client.config.list()
        assert len(configs) == 1
        assert configs[0].key == "c1"

    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.content = b""
        mock_response.parsed = None

        mock_delete.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        # Should not raise
        client.config.delete(_TEST_UUID)

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config(self, mock_update):
        mock_attrs = MagicMock()
        mock_attrs.name = "Updated"
        mock_attrs.key = "test"
        mock_attrs.description = "new desc"
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = mock_resource

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_update.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        result = client.config._update_config(
            config_id=_TEST_UUID,
            name="Updated",
            key="test",
            description="new desc",
        )
        assert result.name == "Updated"

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_get_by_key(self, mock_list):
        mock_attrs = MagicMock()
        mock_attrs.name = "Common"
        mock_attrs.key = "common"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_list.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        cfg = client.config.get(key="common")
        assert cfg.key == "common"

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_by_id_network_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("connection refused")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplConnectionError):
            client.config.get(id=_TEST_UUID)

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_get_by_key_timeout(self, mock_list):
        mock_list.side_effect = httpx.ReadTimeout("timed out")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplTimeoutError):
            client.config.get(key="common")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_by_id_parsed_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_get.return_value = mock_response
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplNotFoundError):
            client.config.get(id=_TEST_UUID)

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_get_by_key_parsed_none(self, mock_list):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_list.return_value = mock_response
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplNotFoundError):
            client.config.get(key="common")

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplConnectionError):
            client.config.create(name="Test")

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_parsed_none(self, mock_create):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_create.return_value = mock_response
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplValidationError):
            client.config.create(name="Test")

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplConnectionError):
            client.config.list()

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_parsed_none(self, mock_list):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_list.return_value = mock_response
        client = SmplClient(api_key="sk_test")
        assert client.config.list() == []

    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplConnectionError):
            client.config.delete(_TEST_UUID)

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplConnectionError):
            client.config._update_config(config_id=_TEST_UUID, name="T")

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_parsed_none(self, mock_update):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_update.return_value = mock_response
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplValidationError):
            client.config._update_config(config_id=_TEST_UUID, name="T")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_by_id_reraises_non_network_error(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.get(id=_TEST_UUID)

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_reraises_non_network_error(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.create(name="Test")

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_list_reraises_non_network_error(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.list()

    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete_reraises_non_network_error(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config.delete(_TEST_UUID)

    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_reraises_non_network_error(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config._update_config(config_id=_TEST_UUID, name="T")


class TestAsyncConfigClient:
    def test_init(self):
        client = AsyncSmplClient(api_key="sk_test")
        assert isinstance(client.config, AsyncConfigClient)

    def test_get_requires_key_or_id(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(ValueError, match="Exactly one"):
                await client.config.get()

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_by_id(self, mock_get):
        mock_attrs = MagicMock()
        mock_attrs.name = "Test"
        mock_attrs.key = "test"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = mock_resource

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_get.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            cfg = await client.config.get(id=_TEST_UUID)
            assert cfg.id == _TEST_UUID

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_get_by_key(self, mock_list):
        mock_attrs = MagicMock()
        mock_attrs.name = "Common"
        mock_attrs.key = "common"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_list.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            cfg = await client.config.get(key="common")
            assert cfg.key == "common"

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_get_by_key_not_found(self, mock_list):
        mock_parsed = MagicMock()
        mock_parsed.data = []

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_list.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplNotFoundError):
                await client.config.get(key="nonexistent")

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create(self, mock_create):
        mock_attrs = MagicMock()
        mock_attrs.name = "New"
        mock_attrs.key = "new"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = mock_resource

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CREATED
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_create.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            cfg = await client.config.create(name="New", key="new")
            assert cfg.name == "New"

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list(self, mock_list):
        mock_attrs = MagicMock()
        mock_attrs.name = "C1"
        mock_attrs.key = "c1"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = [mock_resource]

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_list.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            configs = await client.config.list()
            assert len(configs) == 1

        asyncio.run(_run())

    @patch("smplkit.config.client.delete_config.asyncio_detailed")
    def test_delete(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.content = b""
        mock_response.parsed = None

        mock_delete.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            await client.config.delete(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config(self, mock_update):
        mock_attrs = MagicMock()
        mock_attrs.name = "Updated"
        mock_attrs.key = "test"
        mock_attrs.description = None
        mock_attrs.parent = None
        mock_attrs.values = None
        mock_attrs.environments = None
        mock_attrs.created_at = None
        mock_attrs.updated_at = None

        mock_resource = MagicMock()
        mock_resource.id = _TEST_UUID
        mock_resource.attributes = mock_attrs

        mock_parsed = MagicMock()
        mock_parsed.data = mock_resource

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed

        mock_update.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            result = await client.config._update_config(
                config_id=_TEST_UUID,
                name="Updated",
                key="test",
            )
            assert result.name == "Updated"

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_by_id_network_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("connection refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplConnectionError):
                await client.config.get(id=_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_get_by_key_timeout(self, mock_list):
        mock_list.side_effect = httpx.ReadTimeout("timed out")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplTimeoutError):
                await client.config.get(key="common")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_by_id_parsed_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_get.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplNotFoundError):
                await client.config.get(id=_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_get_by_key_parsed_none(self, mock_list):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_list.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplNotFoundError):
                await client.config.get(key="common")

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplConnectionError):
                await client.config.create(name="Test")

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_parsed_none(self, mock_create):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_create.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplValidationError):
                await client.config.create(name="Test")

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplConnectionError):
                await client.config.list()

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_parsed_none(self, mock_list):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_list.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            result = await client.config.list()
            assert result == []

        asyncio.run(_run())

    @patch("smplkit.config.client.delete_config.asyncio_detailed")
    def test_delete_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplConnectionError):
                await client.config.delete(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplConnectionError):
                await client.config._update_config(config_id=_TEST_UUID, name="T")

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_parsed_none(self, mock_update):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = None
        mock_update.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplValidationError):
                await client.config._update_config(config_id=_TEST_UUID, name="T")

        asyncio.run(_run())

    @patch("smplkit.config.client.get_config.asyncio_detailed")
    def test_get_by_id_reraises_non_network_error(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.get(id=_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.config.client.create_config.asyncio_detailed")
    def test_create_reraises_non_network_error(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.create(name="Test")

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_list_reraises_non_network_error(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.list()

        asyncio.run(_run())

    @patch("smplkit.config.client.delete_config.asyncio_detailed")
    def test_delete_reraises_non_network_error(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config.delete(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.config.client.update_config.asyncio_detailed")
    def test_update_config_reraises_non_network_error(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config._update_config(config_id=_TEST_UUID, name="T")

        asyncio.run(_run())
