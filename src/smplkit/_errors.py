"""Structured SDK error types."""


class SmplkitError(Exception):
    """Base exception for all smplkit SDK errors."""


class AuthenticationError(SmplkitError):
    """Raised when authentication fails."""


class NotFoundError(SmplkitError):
    """Raised when a resource is not found."""


class ValidationError(SmplkitError):
    """Raised when the API rejects a request due to validation."""


class RateLimitError(SmplkitError):
    """Raised when the API rate limit is exceeded."""


class ServerError(SmplkitError):
    """Raised when the API returns a 5xx error."""
