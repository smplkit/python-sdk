"""Basic tests for SDK client initialization."""

import asyncio
from unittest.mock import MagicMock, patch

from smplkit import AsyncSmplClient, SmplClient
from smplkit._ws import SharedWebSocket


def test_smpl_client_init():
    client = SmplClient(api_key="sk_api_test", environment="test")
    assert client._api_key == "sk_api_test"


def test_smpl_client_has_config():
    client = SmplClient(api_key="sk_api_test", environment="test")
    assert hasattr(client, "config")


def test_async_smpl_client_init():
    client = AsyncSmplClient(api_key="sk_api_test", environment="test")
    assert client._api_key == "sk_api_test"


def test_async_smpl_client_has_config():
    client = AsyncSmplClient(api_key="sk_api_test", environment="test")
    assert hasattr(client, "config")


def test_smpl_client_default_import():
    """Verify the public import path works."""
    from smplkit import SmplClient as Client

    assert Client is not None


def test_async_smpl_client_default_import():
    """Verify the public import path works."""
    from smplkit import AsyncSmplClient as Client

    assert Client is not None


def test_smpl_client_context_manager():
    with SmplClient(api_key="sk_api_test", environment="test") as client:
        assert client._api_key == "sk_api_test"


def test_smpl_client_close():
    client = SmplClient(api_key="sk_api_test", environment="test")
    client.close()  # Should not raise


def test_async_smpl_client_context_manager():
    async def _run():
        async with AsyncSmplClient(api_key="sk_api_test", environment="test") as client:
            assert client._api_key == "sk_api_test"

    asyncio.run(_run())


def test_async_smpl_client_close():
    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test", environment="test")
        await client.close()

    asyncio.run(_run())


def test_smpl_client_close_with_existing_client():
    """Exercise close() when an httpx.Client has been created."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    # Force the lazy client to be created by accessing it
    http_client = client._http_client.get_httpx_client()
    assert http_client is not None
    client.close()
    assert client._http_client._client is None


def test_smpl_client_close_idempotent():
    """Closing twice should not raise."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    client.close()
    client.close()


def test_async_smpl_client_close_with_existing_client():
    """Exercise async close() when an httpx.AsyncClient has been created."""

    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test", environment="test")
        # Force the lazy async client to be created
        http_client = client._http_client.get_async_httpx_client()
        assert http_client is not None
        await client.close()
        assert client._http_client._async_client is None

    asyncio.run(_run())


def test_async_ensure_ws_creates_and_starts():
    client = AsyncSmplClient(api_key="sk_api_test", environment="test")
    with patch.object(SharedWebSocket, "start"):
        ws = client._ensure_ws()
        assert ws is not None
        assert client._ws_manager is ws
        ws.start.assert_called_once()


def test_async_ensure_ws_reuses_existing():
    client = AsyncSmplClient(api_key="sk_api_test", environment="test")
    with patch.object(SharedWebSocket, "start"):
        ws1 = client._ensure_ws()
        ws2 = client._ensure_ws()
        assert ws1 is ws2


def test_async_close_stops_ws_manager():
    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test", environment="test")
        with patch.object(SharedWebSocket, "start"):
            ws = client._ensure_ws()
        with patch.object(ws, "stop"):
            await client.close()
            ws.stop.assert_called_once()
        assert client._ws_manager is None

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Sync connect()
# ---------------------------------------------------------------------------


def test_connect_calls_flags_and_config():
    """connect() calls flags._connect_internal() and config._connect_internal()."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    with (
        patch.object(client.flags, "_connect_internal") as mock_flags,
        patch.object(client.config, "_connect_internal") as mock_config,
    ):
        client.connect()
    mock_flags.assert_called_once()
    mock_config.assert_called_once()
    assert client._connected is True


def test_connect_idempotent():
    """Calling connect() twice should only connect once."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    with (
        patch.object(client.flags, "_connect_internal") as mock_flags,
        patch.object(client.config, "_connect_internal"),
    ):
        client.connect()
        client.connect()
    mock_flags.assert_called_once()


@patch("smplkit.client.gen_bulk_register_contexts.sync_detailed")
def test_connect_registers_service(mock_bulk):
    """connect() registers service context when service is set."""
    mock_bulk.return_value = MagicMock()

    client = SmplClient(api_key="sk_api_test", environment="test", service="my-svc")

    with patch.object(client.flags, "_connect_internal"), patch.object(client.config, "_connect_internal"):
        client.connect()

    mock_bulk.assert_called_once()
    _, kwargs = mock_bulk.call_args
    body = kwargs["body"]
    assert body.contexts[0].type_ == "service"
    assert body.contexts[0].key == "my-svc"


def test_connect_no_service_skips_registration():
    """connect() does not register service when service is None."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    with (
        patch.object(client.flags, "_connect_internal"),
        patch.object(client.config, "_connect_internal"),
        patch.object(client, "_register_service_context") as mock_reg,
    ):
        client.connect()
    mock_reg.assert_not_called()


@patch("smplkit.client.gen_bulk_register_contexts.sync_detailed")
def test_connect_service_registration_failure_is_swallowed(mock_bulk):
    """connect() succeeds even if service registration fails."""
    mock_bulk.side_effect = Exception("network error")

    client = SmplClient(api_key="sk_api_test", environment="test", service="my-svc")

    with patch.object(client.flags, "_connect_internal"), patch.object(client.config, "_connect_internal"):
        client.connect()  # Should not raise

    assert client._connected is True


# ---------------------------------------------------------------------------
# Async connect()
# ---------------------------------------------------------------------------


def test_async_connect_calls_flags_and_config():
    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test", environment="test")
        with (
            patch.object(client.flags, "_connect_internal") as mock_flags,
            patch.object(client.config, "_connect_internal") as mock_config,
        ):
            await client.connect()
        mock_flags.assert_called_once()
        mock_config.assert_called_once()
        assert client._connected is True

    asyncio.run(_run())


def test_async_connect_idempotent():
    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test", environment="test")
        with (
            patch.object(client.flags, "_connect_internal") as mock_flags,
            patch.object(client.config, "_connect_internal"),
        ):
            await client.connect()
            await client.connect()
        mock_flags.assert_called_once()

    asyncio.run(_run())


@patch("smplkit.client.gen_bulk_register_contexts.asyncio_detailed")
def test_async_connect_registers_service(mock_bulk):
    mock_bulk.return_value = MagicMock()

    async def _run():
        from unittest.mock import AsyncMock

        client = AsyncSmplClient(api_key="sk_api_test", environment="test", service="my-svc")

        with (
            patch.object(client.flags, "_connect_internal", new_callable=AsyncMock),
            patch.object(client.config, "_connect_internal", new_callable=AsyncMock),
        ):
            await client.connect()

        mock_bulk.assert_called_once()
        _, kwargs = mock_bulk.call_args
        body = kwargs["body"]
        assert body.contexts[0].type_ == "service"
        assert body.contexts[0].key == "my-svc"

    asyncio.run(_run())


@patch("smplkit.client.gen_bulk_register_contexts.asyncio_detailed")
def test_async_connect_service_failure_swallowed(mock_bulk):
    mock_bulk.side_effect = Exception("network error")

    async def _run():
        from unittest.mock import AsyncMock

        client = AsyncSmplClient(api_key="sk_api_test", environment="test", service="my-svc")

        with (
            patch.object(client.flags, "_connect_internal", new_callable=AsyncMock),
            patch.object(client.config, "_connect_internal", new_callable=AsyncMock),
        ):
            await client.connect()  # Should not raise

        assert client._connected is True

    asyncio.run(_run())
