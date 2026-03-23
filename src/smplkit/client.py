"""Top-level SDK client."""

from __future__ import annotations


class SmplkitClient:
    """Entry point for the smplkit SDK.

    Usage:
        from smplkit import SmplkitClient

        client = SmplkitClient(api_key="sk_api_...")
        # client.config, client.flags, client.logging — coming soon
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        sdk_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._sdk_key = sdk_key
        self._base_url = base_url
        # Resource clients will be initialized here as they are built out
