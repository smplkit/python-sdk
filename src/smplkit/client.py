"""Top-level SDK clients — SmplClient (sync) and AsyncSmplClient (async)."""

from __future__ import annotations

import logging
import os

from smplkit._errors import SmplError
from smplkit._generated.app.api.contexts import bulk_register_contexts as gen_bulk_register_contexts
from smplkit._generated.app.models.context_bulk_item import ContextBulkItem
from smplkit._generated.app.models.context_bulk_item_attributes import ContextBulkItemAttributes
from smplkit._generated.app.models.context_bulk_register import ContextBulkRegister
from smplkit._generated.config.client import AuthenticatedClient
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

_NOT_CONNECTED_MESSAGE = "SmplClient is not connected. Call client.connect() first."


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
            checkout_v2 = client.flags.boolFlag("checkout-v2", False)
            client.connect()
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
            from ``SMPLKIT_SERVICE`` if not provided. Used for auto-discovered
            loggers and service context registration.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
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

        self._http_client = AuthenticatedClient(
            base_url=_DEFAULT_BASE_URL,
            token=resolved,
        )
        self._app_http = AuthenticatedClient(
            base_url=_APP_BASE_URL,
            token=resolved,
        )
        self._ws_manager: SharedWebSocket | None = None
        self._connected = False
        self.config = ConfigClient(self)
        self.flags = FlagsClient(self)
        self.logging = LoggingClient(self)

    def connect(self) -> None:
        """Connect to the smplkit platform.

        Opens the shared WebSocket, fetches initial flag and config data,
        and registers the service as a context instance.

        This method is idempotent — calling it multiple times is safe.
        """
        if self._connected:
            return

        # Register service context (fire-and-forget)
        self._register_service_context()

        # Connect flags (fetch definitions, register WS listeners)
        self.flags._connect_internal()

        # Connect config (fetch all, resolve, cache)
        self.config._connect_internal()

        # Connect logging (discover, register, fetch, resolve, apply)
        self.logging._connect_internal()

        self._connected = True

    def _register_service_context(self) -> None:
        """Register the service as a context instance on the app service."""
        try:
            attrs = ContextBulkItemAttributes()
            attrs.additional_properties = {"name": self._service}
            item = ContextBulkItem(type_="service", key=self._service, attributes=attrs)
            body = ContextBulkRegister(contexts=[item])
            gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        except Exception:
            logger.warning("Failed to register service context", exc_info=True)

    def _ensure_ws(self) -> SharedWebSocket:
        """Lazily create and start the shared WebSocket."""
        if self._ws_manager is None:
            self._ws_manager = SharedWebSocket(
                app_base_url=_APP_BASE_URL,
                api_key=self._api_key,
            )
            self._ws_manager.start()
        return self._ws_manager

    def close(self) -> None:
        """Close the underlying HTTP connection pool and shared WebSocket."""
        self.logging._close()
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
            checkout_v2 = client.flags.boolFlag("checkout-v2", False)
            await client.connect()
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
            from ``SMPLKIT_SERVICE`` if not provided. Used for auto-discovered
            loggers and service context registration.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
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

        self._http_client = AuthenticatedClient(
            base_url=_DEFAULT_BASE_URL,
            token=resolved,
        )
        self._app_http = AuthenticatedClient(
            base_url=_APP_BASE_URL,
            token=resolved,
        )
        self._ws_manager: SharedWebSocket | None = None
        self._connected = False
        self.config = AsyncConfigClient(self)
        self.flags = AsyncFlagsClient(self)
        self.logging = AsyncLoggingClient(self)

    async def connect(self) -> None:
        """Connect to the smplkit platform.

        Opens the shared WebSocket, fetches initial flag and config data,
        and registers the service as a context instance.

        This method is idempotent — calling it multiple times is safe.
        """
        if self._connected:
            return

        # Register service context (fire-and-forget)
        await self._register_service_context()

        # Connect flags (fetch definitions, register WS listeners)
        await self.flags._connect_internal()

        # Connect config (fetch all, resolve, cache)
        await self.config._connect_internal()

        # Connect logging (discover, register, fetch, resolve, apply)
        await self.logging._connect_internal()

        self._connected = True

    async def _register_service_context(self) -> None:
        """Register the service as a context instance on the app service."""
        try:
            attrs = ContextBulkItemAttributes()
            attrs.additional_properties = {"name": self._service}
            item = ContextBulkItem(type_="service", key=self._service, attributes=attrs)
            body = ContextBulkRegister(contexts=[item])
            await gen_bulk_register_contexts.asyncio_detailed(client=self._app_http, body=body)
        except Exception:
            logger.warning("Failed to register service context", exc_info=True)

    def _ensure_ws(self) -> SharedWebSocket:
        """Lazily create and start the shared WebSocket."""
        if self._ws_manager is None:
            self._ws_manager = SharedWebSocket(
                app_base_url=_APP_BASE_URL,
                api_key=self._api_key,
            )
            self._ws_manager.start()
        return self._ws_manager

    async def close(self) -> None:
        """Close the underlying HTTP connection pool and shared WebSocket."""
        self.logging._close()
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
