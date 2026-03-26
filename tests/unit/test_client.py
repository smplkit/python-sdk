"""Basic tests for SDK client initialization."""

import asyncio

from smplkit import AsyncSmplClient, SmplClient


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
