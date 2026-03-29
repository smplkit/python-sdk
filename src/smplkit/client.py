"""Top-level SDK clients — SmplClient (sync) and AsyncSmplClient (async)."""

from __future__ import annotations

from smplkit._errors import SmplError
from smplkit._generated.config.client import AuthenticatedClient
from smplkit._resolve import _resolve_api_key
from smplkit.config.client import AsyncConfigClient, ConfigClient

_DEFAULT_BASE_URL = "https://config.smplkit.com"

_NO_API_KEY_MESSAGE = (
    "No API key provided. Set one of:\n"
    "  1. Pass api_key to the constructor\n"
    "  2. Set the SMPLKIT_API_KEY environment variable\n"
    "  3. Add api_key to [default] in ~/.smplkit"
)


class SmplClient:
    """Synchronous entry point for the smplkit SDK.

    Usage::

        from smplkit import SmplClient

        with SmplClient("sk_api_...") as client:
            cfg = client.config.get(key="common")

    The API key is optional. When omitted, it is resolved from the
    ``SMPLKIT_API_KEY`` environment variable or the ``~/.smplkit``
    configuration file.

    All methods that make network requests may raise
    :exc:`SmplConnectionError` if the server is unreachable or
    :exc:`SmplTimeoutError` if the request exceeds the timeout.

    Args:
        api_key: API key for authenticating with the smplkit platform.
            When *None*, the SDK resolves it automatically.
    """

    def __init__(self, api_key: str | None = None) -> None:
        resolved = _resolve_api_key(api_key)
        if resolved is None:
            raise SmplError(_NO_API_KEY_MESSAGE)
        self._api_key = resolved
        self._http_client = AuthenticatedClient(
            base_url=_DEFAULT_BASE_URL,
            token=resolved,
        )
        self.config = ConfigClient(self)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
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

        async with AsyncSmplClient("sk_api_...") as client:
            cfg = await client.config.get(key="common")

    The API key is optional. When omitted, it is resolved from the
    ``SMPLKIT_API_KEY`` environment variable or the ``~/.smplkit``
    configuration file.

    All methods that make network requests may raise
    :exc:`SmplConnectionError` if the server is unreachable or
    :exc:`SmplTimeoutError` if the request exceeds the timeout.

    Args:
        api_key: API key for authenticating with the smplkit platform.
            When *None*, the SDK resolves it automatically.
    """

    def __init__(self, api_key: str | None = None) -> None:
        resolved = _resolve_api_key(api_key)
        if resolved is None:
            raise SmplError(_NO_API_KEY_MESSAGE)
        self._api_key = resolved
        self._http_client = AuthenticatedClient(
            base_url=_DEFAULT_BASE_URL,
            token=resolved,
        )
        self.config = AsyncConfigClient(self)

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        client = self._http_client._async_client
        if client is not None:
            await client.aclose()
            self._http_client._async_client = None

    async def __aenter__(self) -> AsyncSmplClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
