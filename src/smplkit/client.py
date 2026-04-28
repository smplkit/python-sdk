"""Top-level SDK clients — SmplClient (sync) and AsyncSmplClient (async)."""

from __future__ import annotations

import logging
import threading
import traceback

from smplkit._config import _service_url, resolve_config
from smplkit._debug import debug, enable_debug
from smplkit._generated.app.api.contexts import bulk_register_contexts as gen_bulk_register_contexts
from smplkit._generated.app.models.context_bulk_item import ContextBulkItem
from smplkit._generated.app.models.context_bulk_item_attributes import ContextBulkItemAttributes
from smplkit._generated.app.models.context_bulk_register import ContextBulkRegister
from smplkit._generated.config.client import AuthenticatedClient
from smplkit._metrics import _AsyncMetricsReporter, _MetricsReporter
from smplkit._ws import SharedWebSocket
from smplkit.config.client import AsyncConfigClient, ConfigClient
from smplkit.flags.client import AsyncFlagsClient, FlagsClient
from smplkit.logging.client import AsyncLoggingClient, LoggingClient
from smplkit.management._buffer import _ContextRegistrationBuffer
from smplkit.management.client import AsyncManagementClient, ManagementClient

logger = logging.getLogger("smplkit")


class SmplClient:
    """Synchronous entry point for the smplkit SDK.

    Usage::

        from smplkit import SmplClient

        with SmplClient(environment="production", service="my-svc") as client:
            checkout_v2 = client.flags.booleanFlag("checkout-v2", default=False)
            if checkout_v2.get(): ...

    All parameters are optional. When omitted, the SDK resolves them from
    environment variables (``SMPLKIT_*``) or the ``~/.smplkit`` configuration
    file. See ADR-021 for the full resolution algorithm.

    Args:
        api_key: API key for authenticating with the smplkit platform.
        environment: The environment to connect to (e.g. ``"production"``).
        service: Service name (e.g. ``"user-service"``).
        profile: Named profile section to read from ``~/.smplkit``.
        base_domain: Base domain for API requests (default ``"smplkit.com"``).
        scheme: URL scheme (default ``"https"``).
        debug: Enable debug logging in the SDK.
        disable_telemetry: Disable anonymous usage telemetry.
    """

    config: ConfigClient
    flags: FlagsClient
    logging: LoggingClient
    management: ManagementClient

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
        profile: str | None = None,
        base_domain: str | None = None,
        scheme: str | None = None,
        debug: bool | None = None,
        disable_telemetry: bool | None = None,
    ) -> None:
        cfg = resolve_config(
            profile=profile,
            api_key=api_key,
            base_domain=base_domain,
            scheme=scheme,
            environment=environment,
            service=service,
            debug=debug,
            disable_telemetry=disable_telemetry,
        )
        if cfg.debug:
            enable_debug()

        self._api_key = cfg.api_key
        self._environment = cfg.environment
        self._service = cfg.service
        self._base_domain = cfg.base_domain
        self._scheme = cfg.scheme

        if cfg.debug:
            logger.setLevel(logging.DEBUG)

        masked_key = cfg.api_key[:10] + "..." if len(cfg.api_key) > 10 else cfg.api_key
        _debug(
            "lifecycle",
            f"SmplClient init: api_key={masked_key}"
            f" env={cfg.environment!r} service={cfg.service!r}"
            f" base_domain={cfg.base_domain!r} scheme={cfg.scheme!r}"
            f" debug={cfg.debug} disable_telemetry={cfg.disable_telemetry}",
        )

        config_url = _service_url(cfg.scheme, "config", cfg.base_domain)
        app_url = _service_url(cfg.scheme, "app", cfg.base_domain)
        flags_url = _service_url(cfg.scheme, "flags", cfg.base_domain)
        logging_url = _service_url(cfg.scheme, "logging", cfg.base_domain)

        self._http_client = AuthenticatedClient(
            base_url=config_url,
            token=cfg.api_key,
        )
        self._app_http = AuthenticatedClient(
            base_url=app_url,
            token=cfg.api_key,
        )
        self._app_base_url = app_url

        # Metrics reporter
        if cfg.disable_telemetry:
            self._metrics: _MetricsReporter | None = None
        else:
            self._metrics = _MetricsReporter(
                http_client=self._app_http,
                environment=cfg.environment,
                service=cfg.service,
            )

        self._ws_manager: SharedWebSocket | None = None
        self._context_buffer = _ContextRegistrationBuffer()
        self.config = ConfigClient(self)
        self.flags = FlagsClient(
            self, flags_base_url=flags_url, app_base_url=app_url,
            context_buffer=self._context_buffer,
        )
        self.logging = LoggingClient(self, logging_base_url=logging_url, app_base_url=app_url)
        self.management = ManagementClient(
            self, app_base_url=app_url, api_key=cfg.api_key,
            buffer=self._context_buffer,
        )

        # Register service context (fire-and-forget, non-blocking)
        self._init_thread = threading.Thread(target=self._register_service_context, daemon=True)
        self._init_thread.start()

    def _register_service_context(self) -> None:
        """Register the environment and service as context instances on the app service."""
        try:
            svc_attrs = ContextBulkItemAttributes()
            svc_attrs.additional_properties = {"name": self._service}
            svc_item = ContextBulkItem(type_="service", key=self._service, attributes=svc_attrs)
            env_item = ContextBulkItem(type_="environment", key=self._environment)
            body = ContextBulkRegister(contexts=[env_item, svc_item])
            gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        except Exception as exc:
            logger.warning("Failed to register service context (app: %s): %s", self._app_base_url, exc)
            debug("lifecycle", traceback.format_exc().strip())

    def _ensure_ws(self) -> SharedWebSocket:
        """Lazily create and start the shared WebSocket."""
        if self._ws_manager is None:
            self._ws_manager = SharedWebSocket(
                app_base_url=self._app_base_url,
                api_key=self._api_key,
                metrics=self._metrics,
            )
            self._ws_manager.start()
        return self._ws_manager

    def close(self) -> None:
        """Release all resources held by this client."""
        _debug("lifecycle", "SmplClient.close() called")
        if self._metrics is not None:
            self._metrics.close()
        self.logging._close()
        self.flags._close()
        if self._ws_manager is not None:
            self._ws_manager.stop()
            self._ws_manager = None
        client = self._http_client._client
        if client is not None:
            client.close()
            self._http_client._client = None

    def __enter__(self) -> SmplClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AsyncSmplClient:
    """Asynchronous entry point for the smplkit SDK.

    Usage::

        from smplkit import AsyncSmplClient

        async with AsyncSmplClient(environment="production", service="my-svc") as client:
            checkout_v2 = client.flags.booleanFlag("checkout-v2", default=False)
            if checkout_v2.get(): ...

    All parameters are optional. When omitted, the SDK resolves them from
    environment variables (``SMPLKIT_*``) or the ``~/.smplkit`` configuration
    file. See ADR-021 for the full resolution algorithm.
    """

    config: AsyncConfigClient
    flags: AsyncFlagsClient
    logging: AsyncLoggingClient
    management: AsyncManagementClient

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
        profile: str | None = None,
        base_domain: str | None = None,
        scheme: str | None = None,
        debug: bool | None = None,
        disable_telemetry: bool | None = None,
    ) -> None:
        cfg = resolve_config(
            profile=profile,
            api_key=api_key,
            base_domain=base_domain,
            scheme=scheme,
            environment=environment,
            service=service,
            debug=debug,
            disable_telemetry=disable_telemetry,
        )
        if cfg.debug:
            enable_debug()

        self._api_key = cfg.api_key
        self._environment = cfg.environment
        self._service = cfg.service
        self._base_domain = cfg.base_domain
        self._scheme = cfg.scheme

        if cfg.debug:
            logger.setLevel(logging.DEBUG)

        masked_key = cfg.api_key[:10] + "..." if len(cfg.api_key) > 10 else cfg.api_key
        _debug(
            "lifecycle",
            f"AsyncSmplClient init: api_key={masked_key}"
            f" env={cfg.environment!r} service={cfg.service!r}"
            f" base_domain={cfg.base_domain!r} scheme={cfg.scheme!r}"
            f" debug={cfg.debug} disable_telemetry={cfg.disable_telemetry}",
        )

        config_url = _service_url(cfg.scheme, "config", cfg.base_domain)
        app_url = _service_url(cfg.scheme, "app", cfg.base_domain)
        flags_url = _service_url(cfg.scheme, "flags", cfg.base_domain)
        logging_url = _service_url(cfg.scheme, "logging", cfg.base_domain)

        self._http_client = AuthenticatedClient(
            base_url=config_url,
            token=cfg.api_key,
        )
        self._app_http = AuthenticatedClient(
            base_url=app_url,
            token=cfg.api_key,
        )
        self._app_base_url = app_url

        # Metrics reporter
        if cfg.disable_telemetry:
            self._metrics: _AsyncMetricsReporter | None = None
        else:
            self._metrics = _AsyncMetricsReporter(
                http_client=self._app_http,
                environment=cfg.environment,
                service=cfg.service,
            )

        self._ws_manager: SharedWebSocket | None = None
        self._context_buffer = _ContextRegistrationBuffer()
        self.config = AsyncConfigClient(self)
        self.flags = AsyncFlagsClient(
            self, flags_base_url=flags_url, app_base_url=app_url,
            context_buffer=self._context_buffer,
        )
        self.logging = AsyncLoggingClient(self, logging_base_url=logging_url, app_base_url=app_url)
        self.management = AsyncManagementClient(
            self, app_base_url=app_url, api_key=cfg.api_key,
            buffer=self._context_buffer,
        )

        # Register service context (fire-and-forget, non-blocking)
        self._init_thread = threading.Thread(target=self._register_service_context_sync, daemon=True)
        self._init_thread.start()

    def _register_service_context_sync(self) -> None:
        """Sync wrapper for context registration (runs in background thread)."""
        try:
            svc_attrs = ContextBulkItemAttributes()
            svc_attrs.additional_properties = {"name": self._service}
            svc_item = ContextBulkItem(type_="service", key=self._service, attributes=svc_attrs)
            env_item = ContextBulkItem(type_="environment", key=self._environment)
            body = ContextBulkRegister(contexts=[env_item, svc_item])
            gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        except Exception as exc:
            logger.warning("Failed to register service context (app: %s): %s", self._app_base_url, exc)
            debug("lifecycle", traceback.format_exc().strip())

    async def _register_service_context(self) -> None:
        """Register the environment and service as context instances on the app service."""
        try:
            svc_attrs = ContextBulkItemAttributes()
            svc_attrs.additional_properties = {"name": self._service}
            svc_item = ContextBulkItem(type_="service", key=self._service, attributes=svc_attrs)
            env_item = ContextBulkItem(type_="environment", key=self._environment)
            body = ContextBulkRegister(contexts=[env_item, svc_item])
            await gen_bulk_register_contexts.asyncio_detailed(client=self._app_http, body=body)
        except Exception as exc:
            logger.warning("Failed to register service context (app: %s): %s", self._app_base_url, exc)
            debug("lifecycle", traceback.format_exc().strip())

    def _ensure_ws(self) -> SharedWebSocket:
        """Lazily create and start the shared WebSocket."""
        if self._ws_manager is None:
            self._ws_manager = SharedWebSocket(
                app_base_url=self._app_base_url,
                api_key=self._api_key,
                metrics=self._metrics,
            )
            self._ws_manager.start()
        return self._ws_manager

    async def close(self) -> None:
        """Release all resources held by this client."""
        _debug("lifecycle", "AsyncSmplClient.close() called")
        if self._metrics is not None:
            await self._metrics.close()
        self.logging._close()
        self.flags._close()
        if self._ws_manager is not None:
            self._ws_manager.stop()
            self._ws_manager = None
        client = self._http_client._async_client
        if client is not None:
            await client.aclose()
            self._http_client._async_client = None

    async def __aenter__(self) -> AsyncSmplClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


# Use the existing debug function from _debug module.
_debug = debug
