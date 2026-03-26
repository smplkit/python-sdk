"""Structured SDK error types."""

from __future__ import annotations


class SmplError(Exception):
    """Base exception for all smplkit SDK errors."""


class SmplConnectionError(SmplError):
    """Raised when a network request fails."""


class SmplTimeoutError(SmplError):
    """Raised when an operation exceeds its timeout."""


class SmplNotFoundError(SmplError):
    """Raised when a requested resource does not exist."""


class SmplConflictError(SmplError):
    """Raised when an operation conflicts with current state (e.g., deleting a config that has children)."""


class SmplValidationError(SmplError):
    """Raised when the server rejects a request due to validation errors."""
