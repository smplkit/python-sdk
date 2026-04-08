"""Shared helpers used across multiple SDK modules."""

from __future__ import annotations


def key_to_display_name(key: str) -> str:
    """Convert a slug-style key to a human-readable display name.

    ``"checkout-v2"`` → ``"Checkout V2"``
    ``"user_service"`` → ``"User Service"``
    """
    return key.replace("-", " ").replace("_", " ").title()
