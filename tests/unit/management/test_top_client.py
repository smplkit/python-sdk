"""Tests for the management namespace (``client.manage``) and its construction.

After Stage 6 there is no standalone SmplManagementClient — management/CRUD is
the ``client.manage`` namespace on the single :class:`SmplClient`. The contract:

- The namespace construction has zero side effects (no threads, no HTTP).
- All nine CRUD namespaces are wired up; audit/jobs are NOT here (top-level).
- The namespace close() releases HTTP transport resources.
"""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from smplkit import AsyncSmplClient, Error, SmplClient
from smplkit._config import resolve_management_config
from smplkit.management.client import (
    AccountSettingsClient,
    AsyncAccountSettingsClient,
    AsyncConfigClient,
    AsyncContextsClient,
    AsyncContextTypesClient,
    AsyncEnvironmentsClient,
    AsyncFlagsClient,
    AsyncLogGroupsClient,
    AsyncLoggersClient,
    AsyncServicesClient,
    ConfigClient,
    ContextsClient,
    ContextTypesClient,
    EnvironmentsClient,
    FlagsClient,
    LogGroupsClient,
    LoggersClient,
    ServicesClient,
    _AsyncManagementNamespace,
    _ManagementNamespace,
)


# ---------------------------------------------------------------------------
# Sync management namespace
# ---------------------------------------------------------------------------


class TestManagementNamespaceConstruction:
    def test_namespaces_are_wired(self):
        client = SmplClient(api_key="sk_test", base_domain="example.test")
        mgmt = client.manage
        assert isinstance(mgmt.contexts, ContextsClient)
        assert isinstance(mgmt.context_types, ContextTypesClient)
        assert isinstance(mgmt.environments, EnvironmentsClient)
        assert isinstance(mgmt.services, ServicesClient)
        assert isinstance(mgmt.account_settings, AccountSettingsClient)
        assert isinstance(mgmt.config, ConfigClient)
        assert isinstance(mgmt.flags, FlagsClient)
        assert isinstance(mgmt.loggers, LoggersClient)
        assert isinstance(mgmt.log_groups, LogGroupsClient)
        # audit/jobs are top-level (client.audit / client.jobs), never on manage.
        assert not hasattr(mgmt, "audit")
        assert not hasattr(mgmt, "jobs")
        client.close()

    def test_namespace_construction_has_no_side_effects(self):
        """Building the namespace directly must not start threads or make HTTP
        calls — isolated from SmplClient's metrics/audit/jobs wiring."""
        cfg = resolve_management_config(api_key="sk_test", base_domain="example.test")
        before = {t.ident for t in threading.enumerate()}
        with patch("httpx.Client") as mock_sync_client, patch("httpx.AsyncClient") as mock_async_client:
            _ManagementNamespace(cfg)
        after = {t.ident for t in threading.enumerate()}
        assert before == after
        mock_sync_client.assert_not_called()
        mock_async_client.assert_not_called()

    def test_close_closes_all_http_clients(self):
        client = SmplClient(api_key="sk_test", base_domain="example.test")
        mgmt = client.manage
        for attr in ("_app_http", "_config_http", "_flags_http", "_logging_http", "_jobs_http"):
            getattr(mgmt, attr)._client = MagicMock()
        mgmt.close()
        for attr in ("_app_http", "_config_http", "_flags_http", "_logging_http", "_jobs_http"):
            assert getattr(mgmt, attr)._client is None

    def test_close_when_no_clients_initialized(self):
        """Namespace close() is a no-op when no httpx clients were materialized."""
        client = SmplClient(api_key="sk_test", base_domain="example.test")
        client.manage.close()  # should not raise
        client.close()

    def test_instances_have_independent_buffers(self):
        a = SmplClient(api_key="sk_test", base_domain="example.test")
        b = SmplClient(api_key="sk_test", base_domain="example.test")
        assert a.manage._context_buffer is not b.manage._context_buffer
        a.close()
        b.close()


# ---------------------------------------------------------------------------
# Async management namespace
# ---------------------------------------------------------------------------


class TestAsyncManagementNamespaceConstruction:
    def test_namespaces_are_wired(self):
        client = AsyncSmplClient(api_key="sk_test", base_domain="example.test")
        mgmt = client.manage
        assert isinstance(mgmt.contexts, AsyncContextsClient)
        assert isinstance(mgmt.context_types, AsyncContextTypesClient)
        assert isinstance(mgmt.environments, AsyncEnvironmentsClient)
        assert isinstance(mgmt.services, AsyncServicesClient)
        assert isinstance(mgmt.account_settings, AsyncAccountSettingsClient)
        assert isinstance(mgmt.config, AsyncConfigClient)
        assert isinstance(mgmt.flags, AsyncFlagsClient)
        assert isinstance(mgmt.loggers, AsyncLoggersClient)
        assert isinstance(mgmt.log_groups, AsyncLogGroupsClient)
        assert not hasattr(mgmt, "audit")
        assert not hasattr(mgmt, "jobs")
        asyncio.run(client.close())

    def test_namespace_construction_has_no_side_effects(self):
        cfg = resolve_management_config(api_key="sk_test", base_domain="example.test")
        before = {t.ident for t in threading.enumerate()}
        with patch("httpx.Client") as mock_sync, patch("httpx.AsyncClient") as mock_async:
            _AsyncManagementNamespace(cfg)
        after = {t.ident for t in threading.enumerate()}
        assert before == after
        mock_sync.assert_not_called()
        mock_async.assert_not_called()

    def test_close_closes_all_async_clients(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", base_domain="example.test")
            mgmt = client.manage
            for attr in ("_app_http", "_config_http", "_flags_http", "_logging_http", "_jobs_http"):
                ac = AsyncMock()
                ac.aclose = AsyncMock()
                getattr(mgmt, attr)._async_client = ac
            await mgmt.close()
            for attr in ("_app_http", "_config_http", "_flags_http", "_logging_http", "_jobs_http"):
                assert getattr(mgmt, attr)._async_client is None
            await client.close()

        asyncio.run(_run())

    def test_close_when_no_clients_initialized(self):
        async def _run():
            client = AsyncSmplClient(api_key="sk_test", base_domain="example.test")
            await client.manage.close()  # no error
            await client.close()

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# resolve_management_config edge cases
# ---------------------------------------------------------------------------


class TestResolveManagementConfig:
    def test_missing_api_key_raises(self, monkeypatch, tmp_path):
        # api_key is required even for the management resolver (backs the
        # standalone SmplAuditClient/SmplJobsClient transports).
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        monkeypatch.delenv("SMPLKIT_PROFILE", raising=False)
        with pytest.raises(Error, match="No API key provided"):
            resolve_management_config(_home_dir=tmp_path)

    def test_debug_env_var_parsed(self, monkeypatch):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_env")
        monkeypatch.setenv("SMPLKIT_DEBUG", "true")
        from smplkit._config import resolve_management_config

        cfg = resolve_management_config()
        assert cfg.debug is True

    def test_constructor_arg_overrides_env_for_debug(self, monkeypatch):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_env")
        monkeypatch.setenv("SMPLKIT_DEBUG", "false")
        from smplkit._config import resolve_management_config

        cfg = resolve_management_config(debug=True)
        assert cfg.debug is True

    def test_default_base_domain_and_scheme(self, monkeypatch):
        monkeypatch.delenv("SMPLKIT_BASE_DOMAIN", raising=False)
        monkeypatch.delenv("SMPLKIT_SCHEME", raising=False)
        from smplkit._config import resolve_management_config

        cfg = resolve_management_config(api_key="sk_test")
        assert cfg.base_domain == "smplkit.com"
        assert cfg.scheme == "https"

    def test_config_file_provides_api_key_and_debug(self, monkeypatch, tmp_path):
        """Values come from ~/.smplkit when env/args are unset."""
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        monkeypatch.delenv("SMPLKIT_BASE_DOMAIN", raising=False)
        monkeypatch.delenv("SMPLKIT_SCHEME", raising=False)
        monkeypatch.delenv("SMPLKIT_DEBUG", raising=False)
        monkeypatch.delenv("SMPLKIT_PROFILE", raising=False)
        (tmp_path / ".smplkit").write_text(
            "[default]\napi_key = sk_from_file\nbase_domain = file.smplkit.com\ndebug = true\n"
        )
        from smplkit._config import resolve_management_config

        cfg = resolve_management_config(_home_dir=tmp_path)
        assert cfg.api_key == "sk_from_file"
        assert cfg.base_domain == "file.smplkit.com"
        assert cfg.debug is True


# ---------------------------------------------------------------------------
# Model save() with no client raises (the new RuntimeError guard rail)
# ---------------------------------------------------------------------------


class TestModelsRequireClientForSave:
    def test_config_save_without_client(self):
        from smplkit.config.models import Config

        cfg = Config(None, id="x", name="X")
        with pytest.raises(RuntimeError, match="Config was constructed without a client"):
            cfg.save()

    def test_async_config_save_without_client(self):
        from smplkit.config.models import AsyncConfig

        cfg = AsyncConfig(None, id="x", name="X")

        async def _run():
            with pytest.raises(RuntimeError, match="AsyncConfig was constructed without a client"):
                await cfg.save()

        asyncio.run(_run())

    def test_config_build_chain_with_missing_parent_no_client_raises(self):
        from smplkit.config.models import Config

        cfg = Config(None, id="child", name="Child", parent="missing-parent")
        with pytest.raises(RuntimeError, match="cannot resolve parent config"):
            cfg._build_chain([])

    def test_async_config_build_chain_with_missing_parent_no_client_raises(self):
        from smplkit.config.models import AsyncConfig

        cfg = AsyncConfig(None, id="child", name="Child", parent="missing-parent")

        async def _run():
            with pytest.raises(RuntimeError, match="cannot resolve parent config"):
                await cfg._build_chain([])

        asyncio.run(_run())

    def test_flag_save_without_client(self):
        from smplkit.flags.models import Flag

        flag = Flag(None, id="x", name="X", type="BOOLEAN", default=False)
        with pytest.raises(RuntimeError, match="Flag was constructed without a client"):
            flag.save()

    def test_async_flag_save_without_client(self):
        from smplkit.flags.models import AsyncFlag

        flag = AsyncFlag(None, id="x", name="X", type="BOOLEAN", default=False)

        async def _run():
            with pytest.raises(RuntimeError, match="AsyncFlag was constructed without a client"):
                await flag.save()

        asyncio.run(_run())

    def test_logger_save_without_client(self):
        from smplkit.logging.models import SmplLogger

        lg = SmplLogger(None, id="x", name="X")
        with pytest.raises(RuntimeError, match="SmplLogger was constructed without a client"):
            lg.save()

    def test_async_logger_save_without_client(self):
        from smplkit.logging.models import AsyncSmplLogger

        lg = AsyncSmplLogger(None, id="x", name="X")

        async def _run():
            with pytest.raises(RuntimeError, match="AsyncSmplLogger was constructed without a client"):
                await lg.save()

        asyncio.run(_run())

    def test_log_group_save_without_client(self):
        from smplkit.logging.models import SmplLogGroup

        grp = SmplLogGroup(None, id="x", name="X")
        with pytest.raises(RuntimeError, match="SmplLogGroup was constructed without a client"):
            grp.save()

    def test_async_log_group_save_without_client(self):
        from smplkit.logging.models import AsyncSmplLogGroup

        grp = AsyncSmplLogGroup(None, id="x", name="X")

        async def _run():
            with pytest.raises(RuntimeError, match="AsyncSmplLogGroup was constructed without a client"):
                await grp.save()

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# _maybe_reraise_network_error: SDK exception passthrough
# ---------------------------------------------------------------------------


class TestMaybeReraiseNetworkError:
    def test_passes_through_sdk_exceptions(self):
        from smplkit._errors import NotFoundError
        from smplkit.management.client import _maybe_reraise_network_error

        original = NotFoundError("not found", status_code=404)
        with pytest.raises(NotFoundError, match="not found"):
            _maybe_reraise_network_error(original)


# ---------------------------------------------------------------------------
# Runtime ConfigClient internals — fetch error/empty paths
# ---------------------------------------------------------------------------


class TestRuntimeConfigFetchPaths:
    def _client(self):
        from smplkit import SmplClient

        return SmplClient(api_key="sk_test", environment="test", service="svc")

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_fetch_all_configs_network_error(self, mock_list):
        import httpx

        from smplkit._errors import ConnectionError

        mock_list.side_effect = httpx.ConnectError("refused")
        client = self._client()
        with pytest.raises(ConnectionError):
            client.config._fetch_all_configs()

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_fetch_all_configs_parsed_none(self, mock_list):
        mock = MagicMock()
        mock.status_code = 200
        mock.content = b""
        mock.parsed = None
        mock_list.return_value = mock
        client = self._client()
        assert client.config._fetch_all_configs() == []

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_fetch_config_network_error(self, mock_get):
        import httpx

        from smplkit._errors import ConnectionError

        mock_get.side_effect = httpx.ConnectError("refused")
        client = self._client()
        with pytest.raises(ConnectionError):
            client.config._fetch_config("anything")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_fetch_config_parsed_none_returns_none(self, mock_get):
        mock = MagicMock()
        mock.status_code = 200
        mock.content = b""
        mock.parsed = None
        mock_get.return_value = mock
        client = self._client()
        assert client.config._fetch_config("any") is None

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_handle_config_changed_with_none_fetched_returns_quietly(self, mock_get):
        mock = MagicMock()
        mock.status_code = 200
        mock.content = b""
        mock.parsed = None
        mock_get.return_value = mock
        client = self._client()
        client.config._connected = True
        client.config._config_cache = {"x": {"a": 1}}
        client.config._handle_config_changed({"id": "x"})
        # cache unchanged because fetch returned None
        assert client.config._config_cache == {"x": {"a": 1}}

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_async_fetch_all_configs_network_error(self, mock_list):
        from smplkit import AsyncSmplClient
        from smplkit._errors import ConnectionError
        import httpx

        async def _run():
            mock_list.side_effect = httpx.ConnectError("refused")
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(ConnectionError):
                await client.config._fetch_all_configs_async()

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_async_fetch_all_configs_parsed_none(self, mock_list):
        from smplkit import AsyncSmplClient

        async def _run():
            mock = MagicMock()
            mock.status_code = 200
            mock.content = b""
            mock.parsed = None
            mock_list.return_value = mock
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            assert await client.config._fetch_all_configs_async() == []

        asyncio.run(_run())

    @patch("smplkit.config.client.list_configs.sync_detailed")
    def test_fetch_all_configs_reraises_unknown_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = self._client()
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config._fetch_all_configs()

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_fetch_config_reraises_unknown_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")
        client = self._client()
        with pytest.raises(RuntimeError, match="unexpected"):
            client.config._fetch_config("x")

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_fetch_config_returns_built_config(self, mock_get):
        attrs = MagicMock()
        attrs.name = "Common"
        attrs.description = "desc"
        attrs.parent = None
        attrs.items = None
        attrs.environments = None
        attrs.created_at = None
        attrs.updated_at = None
        resource = MagicMock()
        resource.id = "common"
        resource.attributes = attrs
        parsed = MagicMock()
        parsed.data = resource
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b""
        resp.parsed = parsed
        mock_get.return_value = resp
        client = self._client()
        cfg = client.config._fetch_config("common")
        assert cfg is not None
        assert cfg.id == "common"
        assert cfg.name == "Common"

    @patch("smplkit.config.client.list_configs.asyncio_detailed")
    def test_async_fetch_all_configs_reraises_unknown_exception(self, mock_list):
        from smplkit import AsyncSmplClient

        async def _run():
            mock_list.side_effect = RuntimeError("unexpected")
            client = AsyncSmplClient(api_key="sk_test", environment="test", service="svc")
            with pytest.raises(RuntimeError, match="unexpected"):
                await client.config._fetch_all_configs_async()

        asyncio.run(_run())
