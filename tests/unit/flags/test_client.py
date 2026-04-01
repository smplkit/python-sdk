"""Tests for FlagsClient and AsyncFlagsClient management methods."""

import asyncio
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import pytest

from smplkit._errors import (
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
)
from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.flags.client import AsyncFlagsClient, FlagsClient
from smplkit.flags.types import FlagType

_TEST_UUID = "5a0c6be1-0000-0000-0000-000000000001"


def _mock_flag_response(*, key="test-flag", name="Test Flag", type_="BOOLEAN", default=False):
    """Build a mock parsed flag response."""
    mock_values = [MagicMock(name="True", value=True), MagicMock(name="False", value=False)]
    mock_values[0].name = "True"
    mock_values[0].value = True
    mock_values[1].name = "False"
    mock_values[1].value = False

    mock_attrs = MagicMock()
    mock_attrs.key = key
    mock_attrs.name = name
    mock_attrs.type_ = type_
    mock_attrs.default = default
    mock_attrs.values = mock_values
    mock_attrs.description = None
    mock_attrs.environments = MagicMock()
    mock_attrs.environments.__class__.__name__ = "Unset"
    mock_attrs.created_at = None
    mock_attrs.updated_at = None

    # Make environments look like Unset
    from smplkit._generated.flags.types import UNSET

    mock_attrs.environments = UNSET

    mock_resource = MagicMock()
    mock_resource.id = _TEST_UUID
    mock_resource.attributes = mock_attrs

    mock_parsed = MagicMock()
    mock_parsed.data = mock_resource

    return mock_parsed


class TestFlagsClient:
    def test_init(self):
        client = SmplClient(api_key="sk_test")
        assert isinstance(client.flags, FlagsClient)

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create(self, mock_create):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CREATED
        mock_response.content = b""
        mock_response.parsed = _mock_flag_response()
        mock_create.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        flag = client.flags.create(
            "test-flag",
            name="Test Flag",
            type=FlagType.BOOLEAN,
            default=False,
        )
        assert flag.key == "test-flag"
        assert flag.id == _TEST_UUID

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_auto_boolean_values(self, mock_create):
        """Boolean flags should auto-generate values if not provided."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CREATED
        mock_response.content = b""
        mock_response.parsed = _mock_flag_response()
        mock_create.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        client.flags.create("test-flag", name="Test", type=FlagType.BOOLEAN, default=False)

        # Check the body passed to the generated client
        call_kwargs = mock_create.call_args
        body = call_kwargs.kwargs["body"]
        values = body.data.attributes.values
        assert len(values) == 2

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = _mock_flag_response()
        mock_get.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        flag = client.flags.get(_TEST_UUID)
        assert flag.key == "test-flag"

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NOT_FOUND
        mock_response.content = b"Not Found"
        mock_response.parsed = None
        mock_get.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplNotFoundError):
            client.flags.get(_TEST_UUID)

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list(self, mock_list):
        mock_parsed = MagicMock()
        mock_parsed.data = [_mock_flag_response().data]

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed
        mock_list.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        flags = client.flags.list()
        assert len(flags) == 1
        assert flags[0].key == "test-flag"

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.content = b""
        mock_response.parsed = None
        mock_delete.return_value = mock_response

        client = SmplClient(api_key="sk_test")
        client.flags.delete(_TEST_UUID)

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("connection refused")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplConnectionError):
            client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_timeout(self, mock_get):
        mock_get.side_effect = httpx.ReadTimeout("timed out")
        client = SmplClient(api_key="sk_test")
        with pytest.raises(SmplTimeoutError):
            client.flags.get(_TEST_UUID)


class TestAsyncFlagsClient:
    def test_init(self):
        client = AsyncSmplClient(api_key="sk_test")
        assert isinstance(client.flags, AsyncFlagsClient)

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create(self, mock_create):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CREATED
        mock_response.content = b""
        mock_response.parsed = _mock_flag_response()
        mock_create.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            flag = await client.flags.create(
                "test-flag",
                name="Test Flag",
                type=FlagType.BOOLEAN,
                default=False,
            )
            assert flag.key == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = _mock_flag_response()
        mock_get.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            flag = await client.flags.get(_TEST_UUID)
            assert flag.key == "test-flag"

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list(self, mock_list):
        mock_parsed = MagicMock()
        mock_parsed.data = [_mock_flag_response().data]

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.content = b""
        mock_response.parsed = mock_parsed
        mock_list.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            flags = await client.flags.list()
            assert len(flags) == 1

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NO_CONTENT
        mock_response.content = b""
        mock_response.parsed = None
        mock_delete.return_value = mock_response

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            await client.flags.delete(_TEST_UUID)

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = AsyncSmplClient(api_key="sk_test")
            with pytest.raises(SmplConnectionError):
                await client.flags.create("test", name="Test", type=FlagType.BOOLEAN, default=False)

        asyncio.run(_run())


class TestFlagsRuntime:
    """Test runtime behavior with mocked flag store."""

    def test_flag_handles_return_code_default_before_connect(self):
        client = SmplClient(api_key="sk_test")
        handle = client.flags.boolFlag("test", False)
        assert handle.get() is False

    def test_stats_initial(self):
        client = SmplClient(api_key="sk_test")
        stats = client.flags.stats()
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

    def test_connection_status_initial(self):
        client = SmplClient(api_key="sk_test")
        assert client.flags.connection_status() == "disconnected"

    def test_context_provider_decorator(self):
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")

        @client.flags.context_provider
        def provider():
            return [Context("user", "u-1")]

        assert client.flags._context_provider is provider

    def test_on_change_decorator(self):
        client = SmplClient(api_key="sk_test")

        @client.flags.on_change
        def listener(event):
            pass

        assert len(client.flags._global_listeners) == 1

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_evaluate_handle_with_connected_store(self, mock_list):
        """Test that evaluation works against a populated flag store."""
        client = SmplClient(api_key="sk_test")
        ns = client.flags

        # Manually populate the store (simulating connect)
        ns._connected = True
        ns._environment = "staging"
        ns._flag_store = {
            "checkout-v2": {
                "key": "checkout-v2",
                "name": "Checkout V2",
                "type": "BOOLEAN",
                "default": False,
                "values": [],
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [
                            {
                                "logic": {"==": [{"var": "user.plan"}, "enterprise"]},
                                "value": True,
                            },
                        ],
                    },
                },
            },
        }

        from smplkit.flags.types import Context

        handle = ns.boolFlag("checkout-v2", False)

        # With matching context
        result = handle.get(context=[Context("user", "u-1", plan="enterprise")])
        assert result is True

        # With non-matching context
        result = handle.get(context=[Context("user", "u-2", plan="free")])
        assert result is False

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_cache_hits_on_repeated_evaluation(self, mock_list):
        """Repeated evaluations with same context should hit cache."""
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags
        ns._connected = True
        ns._environment = "staging"
        ns._flag_store = {
            "flag-a": {
                "key": "flag-a",
                "type": "BOOLEAN",
                "default": False,
                "environments": {
                    "staging": {"enabled": True, "rules": []},
                },
            },
        }

        handle = ns.boolFlag("flag-a", False)
        ctx = [Context("user", "u-1", plan="free")]

        handle.get(context=ctx)  # miss
        handle.get(context=ctx)  # hit
        handle.get(context=ctx)  # hit

        stats = ns.stats()
        assert stats.cache_misses == 1
        assert stats.cache_hits == 2

    def test_cache_cleared_on_change(self):
        client = SmplClient(api_key="sk_test")
        ns = client.flags
        ns._cache.put("k", "v")
        ns._cache.clear()
        hit, _ = ns._cache.get("k")
        assert hit is False


class TestRegister:
    """Tests for explicit context registration via register()."""

    def test_register_single_context(self):
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(Context("user", "u-1", plan="enterprise"))

        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["id"] == "user:u-1"
        assert batch[0]["name"] == "u-1"
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_register_single_context_with_name(self):
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(Context("user", "u-1", name="Alice Smith", plan="enterprise"))

        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["id"] == "user:u-1"
        assert batch[0]["name"] == "Alice Smith"
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_register_list_of_contexts(self):
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(
            [
                Context("user", "u-1", plan="enterprise"),
                Context("account", "acme-corp", region="us"),
            ]
        )

        batch = ns._context_buffer.drain()
        assert len(batch) == 2
        assert batch[0]["id"] == "user:u-1"
        assert batch[1]["id"] == "account:acme-corp"

    def test_register_before_connect(self):
        """Contexts registered before connect() are queued, not lost."""
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        assert not ns._connected

        ns.register(Context("user", "u-1", plan="free"))
        ns.register(Context("account", "small-biz", region="eu"))

        batch = ns._context_buffer.drain()
        assert len(batch) == 2

    def test_register_deduplication(self):
        """Same (type, key) pair should not be queued twice."""
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(Context("user", "u-1", plan="enterprise"))
        ns.register(Context("user", "u-1", plan="free"))  # same type+key

        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        # First registration wins
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_register_different_keys_not_deduplicated(self):
        """Different keys for the same type should both be queued."""
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(Context("user", "u-1", plan="enterprise"))
        ns.register(Context("user", "u-2", plan="free"))

        batch = ns._context_buffer.drain()
        assert len(batch) == 2

    def test_register_integrates_with_flush(self):
        """Explicitly registered contexts appear in flushed batch."""
        from smplkit.flags.types import Context

        client = SmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(Context("user", "u-1", plan="enterprise"))

        # Also add via observe (simulating context provider side-effect)
        ns._context_buffer.observe([Context("account", "acme-corp", region="us")])

        batch = ns._context_buffer.drain()
        assert len(batch) == 2
        ids = {b["id"] for b in batch}
        assert ids == {"user:u-1", "account:acme-corp"}

    def test_async_register_single_context(self):
        from smplkit.flags.types import Context

        client = AsyncSmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(Context("user", "u-1", plan="enterprise"))

        batch = ns._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["id"] == "user:u-1"

    def test_async_register_list(self):
        from smplkit.flags.types import Context

        client = AsyncSmplClient(api_key="sk_test")
        ns = client.flags

        ns.register(
            [
                Context("user", "u-1"),
                Context("account", "acme-corp"),
            ]
        )

        batch = ns._context_buffer.drain()
        assert len(batch) == 2
