"""Top-level SDK clients — SmplClient (sync) and AsyncSmplClient (async)."""

from __future__ import annotations

import logging
import os

from smplkit._errors import SmplError
from smplkit._generated.config.client import AuthenticatedClient
from smplkit._resolve import _resolve_api_key
from smplkit._ws import SharedWebSocket
from smplkit.config.client import AsyncConfigClient, ConfigClient
from smplkit.flags.client import AsyncFlagsClient, FlagsClient

logger = logging.getLogger("smplkit")

_DEFAULT_BASE_URL = "https://config.smplkit.com"
_APP_BASE_URL = "https://app.smplkit.com"

_NO_API_KEY_MESSAGE = (
    "No API key provided. Set one of:\n"
    "  1. Pass api_key to the constructor\n"
    "  2. Set the SMPLKIT_API_KEY environment variable\n"
    "  3. Create a ~/.smplkit file with:\n"
    "     [default]\n"
    "     api_key = your_key_here"
)

_NO_ENVIRONMENT_MESSAGE = (
    "No environment provided. Set one of:\n"
    "  1. Pass environment to the constructor\n"
    "  2. Set the SMPLKIT_ENVIRONMENT environment variable"
)

_NOT_CONNECTED_MESSAGE = "SmplClient is not connected. Call client.connect() first."


class SmplClient:
    """Synchronous entry point for the smplkit SDK.

    Usage::

        from smplkit import SmplClient

        with SmplClient("sk_api_...", environment="production") as client:
            checkout_v2 = client.flags.boolFlag("checkout-v2", False)
            client.connect()
            if checkout_v2.get(): ...

    The API key is optional. When omitted, it is resolved from the
    ``SMPLKIT_API_KEY`` environment variable or the ``~/.smplkit``
    configuration file.

    Args:
        api_key: API key for authenticating with the smplkit platform.
            When *None*, the SDK resolves it automatically.
        environment: The environment to connect to (e.g. ``"production"``).
            Required — resolved from ``SMPLKIT_ENVIRONMENT`` if not provided.
        service: Optional service name. When set, the SDK automatically
            registers the service as a context instance and includes it
            in flag evaluation context.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
    ) -> None:
        resolved = _resolve_api_key(api_key)
        if resolved is None:
            raise SmplError(_NO_API_KEY_MESSAGE)
        self._api_key = resolved

        resolved_env = environment or os.environ.get("SMPLKIT_ENVIRONMENT")
        if not resolved_env:
            raise SmplError(_NO_ENVIRONMENT_MESSAGE)
        self._environment = resolved_env
        self._service = service or os.environ.get("SMPLKIT_SERVICE") or None

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

    def connect(self) -> None:
        """Connect to the smplkit platform.

        Opens the shared WebSocket, fetches initial flag and config data,
        and registers the service as a context instance (if provided).

        This method is idempotent — calling it multiple times is safe.
        """
        if self._connected:
            return

        # Register service context (fire-and-forget)
        if self._service:
            self._register_service_context()

        # Connect flags (fetch definitions, register WS listeners)
        self.flags._connect_internal()

        # Connect config (fetch all, resolve, cache)
        self.config._connect_internal()

        self._connected = True

    def _register_service_context(self) -> None:
        """Register the service as a context instance on the app service."""
        try:
            self._app_http.get_httpx_client().put(
                "/api/v1/contexts/bulk",
                json={
                    "contexts": [
                        {
                            "type": "service",
                            "key": self._service,
                            "attributes": {"name": self._service},
                        }
                    ]
                },
            )
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

        async with AsyncSmplClient("sk_api_...", environment="production") as client:
            checkout_v2 = client.flags.boolFlag("checkout-v2", False)
            await client.connect()
            if checkout_v2.get(): ...

    The API key is optional. When omitted, it is resolved from the
    ``SMPLKIT_API_KEY`` environment variable or the ``~/.smplkit``
    configuration file.

    Args:
        api_key: API key for authenticating with the smplkit platform.
            When *None*, the SDK resolves it automatically.
        environment: The environment to connect to (e.g. ``"production"``).
            Required — resolved from ``SMPLKIT_ENVIRONMENT`` if not provided.
        service: Optional service name. When set, the SDK automatically
            registers the service as a context instance and includes it
            in flag evaluation context.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        service: str | None = None,
    ) -> None:
        resolved = _resolve_api_key(api_key)
        if resolved is None:
            raise SmplError(_NO_API_KEY_MESSAGE)
        self._api_key = resolved

        resolved_env = environment or os.environ.get("SMPLKIT_ENVIRONMENT")
        if not resolved_env:
            raise SmplError(_NO_ENVIRONMENT_MESSAGE)
        self._environment = resolved_env
        self._service = service or os.environ.get("SMPLKIT_SERVICE") or None

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

    async def connect(self) -> None:
        """Connect to the smplkit platform.

        Opens the shared WebSocket, fetches initial flag and config data,
        and registers the service as a context instance (if provided).

        This method is idempotent — calling it multiple times is safe.
        """
        if self._connected:
            return

        # Register service context (fire-and-forget)
        if self._service:
            await self._register_service_context()

        # Connect flags (fetch definitions, register WS listeners)
        await self.flags._connect_internal()

        # Connect config (fetch all, resolve, cache)
        await self.config._connect_internal()

        self._connected = True

    async def _register_service_context(self) -> None:
        """Register the service as a context instance on the app service."""
        try:
            await self._app_http.get_async_httpx_client().put(
                "/api/v1/contexts/bulk",
                json={
                    "contexts": [
                        {
                            "type": "service",
                            "key": self._service,
                            "attributes": {"name": self._service},
                        }
                    ]
                },
            )
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
