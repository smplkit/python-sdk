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


def test_smpl_client_no_connect_method():
    """connect() has been removed from SmplClient."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    assert not hasattr(client, "connect")


def test_async_smpl_client_no_connect_method():
    """connect() has been removed from AsyncSmplClient."""
    client = AsyncSmplClient(api_key="sk_api_test", environment="test")
    assert not hasattr(client, "connect")


@patch("smplkit.client.gen_bulk_register_contexts.sync_detailed")
def test_service_context_registered_on_init(mock_bulk):
    """Environment and service contexts are registered during __init__ (fire-and-forget)."""
    mock_bulk.return_value = MagicMock()

    client = SmplClient(api_key="sk_api_test", environment="test", service="my-svc")
    client._init_thread.join(timeout=2.0)

    mock_bulk.assert_called_once()
    _, kwargs = mock_bulk.call_args
    body = kwargs["body"]
    assert len(body.contexts) == 2
    assert body.contexts[0].type_ == "environment"
    assert body.contexts[0].key == "test"
    assert body.contexts[1].type_ == "service"
    assert body.contexts[1].key == "my-svc"
    assert client._api_key == "sk_api_test"


@patch("smplkit.client.gen_bulk_register_contexts.sync_detailed")
def test_service_registration_failure_on_init_is_swallowed(mock_bulk):
    """Init succeeds even if service registration fails."""
    mock_bulk.side_effect = Exception("network error")

    client = SmplClient(api_key="sk_api_test", environment="test", service="my-svc")
    client._init_thread.join(timeout=2.0)
    assert client._api_key == "sk_api_test"


@patch("smplkit.client.gen_bulk_register_contexts.sync_detailed")
def test_async_service_context_registered_on_init(mock_bulk):
    """AsyncSmplClient also registers environment and service contexts via background thread."""
    mock_bulk.return_value = MagicMock()

    client = AsyncSmplClient(api_key="sk_api_test", environment="test", service="my-svc")
    client._init_thread.join(timeout=2.0)

    mock_bulk.assert_called_once()
    _, kwargs = mock_bulk.call_args
    body = kwargs["body"]
    assert len(body.contexts) == 2
    assert body.contexts[0].type_ == "environment"
    assert body.contexts[0].key == "test"
    assert body.contexts[1].type_ == "service"
    assert body.contexts[1].key == "my-svc"
    assert client._api_key == "sk_api_test"


@patch("smplkit.client.gen_bulk_register_contexts.sync_detailed")
def test_async_service_registration_failure_on_init_is_swallowed(mock_bulk):
    """AsyncSmplClient init succeeds even if service registration fails."""
    mock_bulk.side_effect = Exception("network error")

    client = AsyncSmplClient(api_key="sk_api_test", environment="test", service="my-svc")
    client._init_thread.join(timeout=2.0)
    assert client._api_key == "sk_api_test"


@patch("smplkit.client.gen_bulk_register_contexts.asyncio_detailed")
def test_async_register_service_context_success(mock_bulk):
    """The async _register_service_context method works end to end."""
    mock_bulk.return_value = MagicMock()

    client = AsyncSmplClient(api_key="sk_api_test", environment="test", service="my-svc")
    # Wait for the sync background thread (from __init__) to finish first
    client._init_thread.join(timeout=2.0)

    asyncio.run(client._register_service_context())
    mock_bulk.assert_called_once()
    _, kwargs = mock_bulk.call_args
    body = kwargs["body"]
    assert len(body.contexts) == 2
    assert body.contexts[0].type_ == "environment"
    assert body.contexts[0].key == "test"
    assert body.contexts[1].type_ == "service"
    assert body.contexts[1].key == "my-svc"


@patch("smplkit.client.gen_bulk_register_contexts.asyncio_detailed")
def test_async_register_service_context_failure_swallowed(mock_bulk):
    """The async _register_service_context swallows exceptions."""
    mock_bulk.side_effect = Exception("network error")

    client = AsyncSmplClient(api_key="sk_api_test", environment="test", service="my-svc")
    client._init_thread.join(timeout=2.0)

    # Should not raise
    asyncio.run(client._register_service_context())


# ---------------------------------------------------------------------------
# base_domain / scheme tests
# ---------------------------------------------------------------------------


def test_smpl_client_default_urls():
    """Default URLs are production smplkit.com with https."""
    client = SmplClient(api_key="sk_api_test", environment="test")
    assert client._http_client._base_url == "https://config.smplkit.com"
    assert client._app_base_url == "https://app.smplkit.com"
    assert client.flags._flags_http._base_url == "https://flags.smplkit.com"
    assert client.flags._app_http._base_url == "https://app.smplkit.com"
    assert client.logging._logging_http._base_url == "https://logging.smplkit.com"


def test_smpl_client_custom_base_domain():
    """Custom base_domain overrides all service URLs."""
    client = SmplClient(
        api_key="sk_api_test",
        environment="test",
        base_domain="localhost",
        scheme="http",
    )
    assert client._http_client._base_url == "http://config.localhost"
    assert client._app_base_url == "http://app.localhost"
    assert client.flags._flags_http._base_url == "http://flags.localhost"
    assert client.flags._app_http._base_url == "http://app.localhost"
    assert client.logging._logging_http._base_url == "http://logging.localhost"


def test_smpl_client_custom_domain_ws_url():
    """_ensure_ws uses the computed app URL."""
    client = SmplClient(
        api_key="sk_api_test",
        environment="test",
        base_domain="localhost",
        scheme="http",
    )
    with patch.object(SharedWebSocket, "start"):
        ws = client._ensure_ws()
    assert ws._app_base_url == "http://app.localhost"


def test_async_smpl_client_default_urls():
    """AsyncSmplClient default URLs are production smplkit.com with https."""
    client = AsyncSmplClient(api_key="sk_api_test", environment="test")
    assert client._http_client._base_url == "https://config.smplkit.com"
    assert client._app_base_url == "https://app.smplkit.com"
    assert client.flags._flags_http._base_url == "https://flags.smplkit.com"
    assert client.logging._logging_http._base_url == "https://logging.smplkit.com"


def test_async_smpl_client_custom_base_domain():
    """AsyncSmplClient custom base_domain overrides all service URLs."""
    client = AsyncSmplClient(
        api_key="sk_api_test",
        environment="test",
        base_domain="localhost",
        scheme="http",
    )
    assert client._http_client._base_url == "http://config.localhost"
    assert client._app_base_url == "http://app.localhost"
    assert client.flags._flags_http._base_url == "http://flags.localhost"
    assert client.flags._app_http._base_url == "http://app.localhost"
    assert client.logging._logging_http._base_url == "http://logging.localhost"


def test_async_smpl_client_custom_domain_ws_url():
    """AsyncSmplClient _ensure_ws uses the computed app URL."""
    client = AsyncSmplClient(
        api_key="sk_api_test",
        environment="test",
        base_domain="localhost",
        scheme="http",
    )
    with patch.object(SharedWebSocket, "start"):
        ws = client._ensure_ws()
    assert ws._app_base_url == "http://app.localhost"


def test_async_logging_client_stores_logging_base_url():
    """AsyncLoggingClient stores logging_base_url for WS refresh thread."""
    client = AsyncSmplClient(
        api_key="sk_api_test",
        environment="test",
        base_domain="localhost",
        scheme="http",
    )
    assert client.logging._logging_base_url == "http://logging.localhost"
