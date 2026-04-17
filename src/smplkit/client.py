"""Top-level SDK clients — SmplClient (sync) and AsyncSmplClient (async)."""

from __future__ import annotations

import logging
import os
import threading

from smplkit._debug import debug
from smplkit._errors import SmplError
from smplkit._generated.app.api.contexts import bulk_register_contexts as gen_bulk_register_contexts
from smplkit._generated.app.models.context_bulk_item import ContextBulkItem
from smplkit._generated.app.models.context_bulk_item_attributes import ContextBulkItemAttributes
from smplkit._generated.app.models.context_bulk_register import ContextBulkRegister
from smplkit._generated.config.client import AuthenticatedClient
from smplkit._metrics import _AsyncMetricsReporter, _MetricsReporter
from smplkit._resolve import _resolve_api_key
from smplkit._ws import SharedWebSocket
from smplkit.config.client import AsyncConfigClient, ConfigClient
from smplkit.flags.client import AsyncFlagsClient, FlagsClient
from smplkit.logging.client import AsyncLoggingClient, LoggingClient

logger = logging.getLogger("smplkit")

_DEFAULT_BASE_URL = "https://config.smplkit.com"
_APP_BASE_URL = "https://app.smplkit.com"

_NO_ENVIRONMENT_MESSAGE = (
    "No environment provided. Set one of:\n"
    "  1. Pass environment to the constructor\n"
    "  2. Set the SMPLKIT_ENVIRONMENT environment variable"
)

_NO_SERVICE_MESSAGE = (
    "No service provided. Set one of:\n"
    "  1. Pass service to the constructor\n"
    "  2. Set the SMPLKIT_SERVICE environment variable"
)


def _no_api_key_message(environment: str) -> str:
    return (
        "No API key provided. Set one of:\n"
        "  1. Pass api_key to the constructor\n"
        "  2. Set the SMPLKIT_API_KEY environment variable\n"
        "  3. Create a ~/.smplkit file with:\n"
        f"     [{environment}]\n"
        "     api_key = your_key_here"
    )


class SmplClient:
    """Synchronous entry point for the smplkit SDK.

    Usage::

        from smplkit import SmplClient

        with SmplClient("sk_api_...", environment="production", service="my-svc") as client:
            checkout_v2 = client.flags.booleanFlag("checkout-v2", default=False)
            if checkout_v2.get(): ...

    The API key is optional. When omitted, it is resolved from the
    ``SMPLKIT_API_KEY`` environment variable or the ``~/.smplkit``
    configuration file (``[{environment}]`` section, then ``[default]``).

    Args:
        api_key: API key for authenticating with the smplkit platform.
            When *None*, the SDK resolves it automatically.
        environment: The environment to connect to (e.g. ``"production"``).
            Required — resolved from ``SMPLKIT_ENVIRONMENT`` if not provided.
        service: Service name (e.g. ``"user-service"``). Required — resolved
            from ``SMPLKIT_SERVICE`` if not provided.
    """

    config: ConfigClient
    flags: FlagsClient
    logging: LoggingClient

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
        disable_telemetry: bool = False,
    ) -> None:
        # 1. Resolve environment
        resolved_env = environment or os.environ.get("SMPLKIT_ENVIRONMENT")
        if not resolved_env:
            raise SmplError(_NO_ENVIRONMENT_MESSAGE)
        self._environment = resolved_env

        # 2. Resolve service
        resolved_svc = service or os.environ.get("SMPLKIT_SERVICE")
        if not resolved_svc:
            raise SmplError(_NO_SERVICE_MESSAGE)
        self._service = resolved_svc

        # 3. Resolve API key (needs environment for ~/.smplkit section lookup)
        resolved = _resolve_api_key(api_key, self._environment)
        if resolved is None:
            raise SmplError(_no_api_key_message(self._environment))
        self._api_key = resolved
        debug(
            "lifecycle",
            f"SmplClient init: api_key={resolved[:10]}...{resolved[-4:]}"
            f" env={self._environment!r} service={self._service!r}",
        )

        self._http_client = AuthenticatedClient(
            base_url=_DEFAULT_BASE_URL,
            token=resolved,
        )
        self._app_http = AuthenticatedClient(
            base_url=_APP_BASE_URL,
            token=resolved,
        )

        # 4. Metrics reporter
        if disable_telemetry:
            self._metrics: _MetricsReporter | None = None
        else:
            self._metrics = _MetricsReporter(
                http_client=self._app_http,
                environment=self._environment,
                service=self._service,
            )

        self._ws_manager: SharedWebSocket | None = None
        self.config = ConfigClient(self)
        self.flags = FlagsClient(self)
        self.logging = LoggingClient(self)

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
        except Exception:
            logger.warning("Failed to register service context", exc_info=True)

    def _ensure_ws(self) -> SharedWebSocket:
        """Lazily create and start the shared WebSocket."""
        if self._ws_manager is None:
            self._ws_manager = SharedWebSocket(
                app_base_url=_APP_BASE_URL,
                api_key=self._api_key,
                metrics=self._metrics,
            )
            self._ws_manager.start()
        return self._ws_manager

    def close(self) -> None:
        """Release all resources held by this client."""
        debug("lifecycle", "SmplClient.close() called")
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

        async with AsyncSmplClient("sk_api_...", environment="production", service="my-svc") as client:
            checkout_v2 = client.flags.booleanFlag("checkout-v2", default=False)
            if checkout_v2.get(): ...

    The API key is optional. When omitted, it is resolved from the
    ``SMPLKIT_API_KEY`` environment variable or the ``~/.smplkit``
    configuration file (``[{environment}]`` section, then ``[default]``).

    Args:
        api_key: API key for authenticating with the smplkit platform.
            When *None*, the SDK resolves it automatically.
        environment: The environment to connect to (e.g. ``"production"``).
            Required — resolved from ``SMPLKIT_ENVIRONMENT`` if not provided.
        service: Service name (e.g. ``"user-service"``). Required — resolved
            from ``SMPLKIT_SERVICE`` if not provided.
    """

    config: AsyncConfigClient
    flags: AsyncFlagsClient
    logging: AsyncLoggingClient

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
        disable_telemetry: bool = False,
    ) -> None:
        # 1. Resolve environment
        resolved_env = environment or os.environ.get("SMPLKIT_ENVIRONMENT")
        if not resolved_env:
            raise SmplError(_NO_ENVIRONMENT_MESSAGE)
        self._environment = resolved_env

        # 2. Resolve service
        resolved_svc = service or os.environ.get("SMPLKIT_SERVICE")
        if not resolved_svc:
            raise SmplError(_NO_SERVICE_MESSAGE)
        self._service = resolved_svc

        # 3. Resolve API key (needs environment for ~/.smplkit section lookup)
        resolved = _resolve_api_key(api_key, self._environment)
        if resolved is None:
            raise SmplError(_no_api_key_message(self._environment))
        self._api_key = resolved
        debug(
            "lifecycle",
            f"AsyncSmplClient init: api_key={resolved[:10]}...{resolved[-4:]}"
            f" env={self._environment!r} service={self._service!r}",
        )

        self._http_client = AuthenticatedClient(
            base_url=_DEFAULT_BASE_URL,
            token=resolved,
        )
        self._app_http = AuthenticatedClient(
            base_url=_APP_BASE_URL,
            token=resolved,
        )

        # 4. Metrics reporter
        if disable_telemetry:
            self._metrics: _AsyncMetricsReporter | None = None
        else:
            self._metrics = _AsyncMetricsReporter(
                http_client=self._app_http,
                environment=self._environment,
                service=self._service,
            )

        self._ws_manager: SharedWebSocket | None = None
        self.config = AsyncConfigClient(self)
        self.flags = AsyncFlagsClient(self)
        self.logging = AsyncLoggingClient(self)

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
        except Exception:
            logger.warning("Failed to register service context", exc_info=True)

    async def _register_service_context(self) -> None:
        """Register the environment and service as context instances on the app service."""
        try:
            svc_attrs = ContextBulkItemAttributes()
            svc_attrs.additional_properties = {"name": self._service}
            svc_item = ContextBulkItem(type_="service", key=self._service, attributes=svc_attrs)
            env_item = ContextBulkItem(type_="environment", key=self._environment)
            body = ContextBulkRegister(contexts=[env_item, svc_item])
            await gen_bulk_register_contexts.asyncio_detailed(client=self._app_http, body=body)
        except Exception:
            logger.warning("Failed to register service context", exc_info=True)

    def _ensure_ws(self) -> SharedWebSocket:
        """Lazily create and start the shared WebSocket."""
        if self._ws_manager is None:
            self._ws_manager = SharedWebSocket(
                app_base_url=_APP_BASE_URL,
                api_key=self._api_key,
                metrics=self._metrics,
            )
            self._ws_manager.start()
        return self._ws_manager

    async def close(self) -> None:
        """Release all resources held by this client."""
        debug("lifecycle", "AsyncSmplClient.close() called")
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
