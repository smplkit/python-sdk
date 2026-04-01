"""Basic tests for SDK client initialization."""

import asyncio
from unittest.mock import patch

from smplkit import AsyncSmplClient, SmplClient
from smplkit._ws import SharedWebSocket


def test_smpl_client_init():
    client = SmplClient(api_key="sk_api_test")
    assert client._api_key == "sk_api_test"


def test_smpl_client_has_config():
    client = SmplClient(api_key="sk_api_test")
    assert hasattr(client, "config")


def test_async_smpl_client_init():
    client = AsyncSmplClient(api_key="sk_api_test")
    assert client._api_key == "sk_api_test"


def test_async_smpl_client_has_config():
    client = AsyncSmplClient(api_key="sk_api_test")
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
    with SmplClient(api_key="sk_api_test") as client:
        assert client._api_key == "sk_api_test"


def test_smpl_client_close():
    client = SmplClient(api_key="sk_api_test")
    client.close()  # Should not raise


def test_async_smpl_client_context_manager():
    async def _run():
        async with AsyncSmplClient(api_key="sk_api_test") as client:
            assert client._api_key == "sk_api_test"

    asyncio.run(_run())


def test_async_smpl_client_close():
    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test")
        await client.close()

    asyncio.run(_run())


def test_smpl_client_close_with_existing_client():
    """Exercise close() when an httpx.Client has been created."""
    client = SmplClient(api_key="sk_api_test")
    # Force the lazy client to be created by accessing it
    http_client = client._http_client.get_httpx_client()
    assert http_client is not None
    client.close()
    assert client._http_client._client is None


def test_smpl_client_close_idempotent():
    """Closing twice should not raise."""
    client = SmplClient(api_key="sk_api_test")
    client.close()
    client.close()


def test_async_smpl_client_close_with_existing_client():
    """Exercise async close() when an httpx.AsyncClient has been created."""

    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test")
        # Force the lazy async client to be created
        http_client = client._http_client.get_async_httpx_client()
        assert http_client is not None
        await client.close()
        assert client._http_client._async_client is None

    asyncio.run(_run())


def test_async_ensure_ws_creates_and_starts():
    client = AsyncSmplClient(api_key="sk_api_test")
    with patch.object(SharedWebSocket, "start"):
        ws = client._ensure_ws()
        assert ws is not None
        assert client._ws_manager is ws
        ws.start.assert_called_once()


def test_async_ensure_ws_reuses_existing():
    client = AsyncSmplClient(api_key="sk_api_test")
    with patch.object(SharedWebSocket, "start"):
        ws1 = client._ensure_ws()
        ws2 = client._ensure_ws()
        assert ws1 is ws2


def test_async_close_stops_ws_manager():
    async def _run():
        client = AsyncSmplClient(api_key="sk_api_test")
        with patch.object(SharedWebSocket, "start"):
            ws = client._ensure_ws()
        with patch.object(ws, "stop"):
            await client.close()
            ws.stop.assert_called_once()
        assert client._ws_manager is None

    asyncio.run(_run())
