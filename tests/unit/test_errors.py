"""Tests for SDK error types."""

from smplkit._errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SmplkitError,
    ValidationError,
)


def test_smplkit_error_is_base():
    assert issubclass(AuthenticationError, SmplkitError)
    assert issubclass(NotFoundError, SmplkitError)
    assert issubclass(ValidationError, SmplkitError)
    assert issubclass(RateLimitError, SmplkitError)
    assert issubclass(ServerError, SmplkitError)


def test_smplkit_error_is_exception():
    assert issubclass(SmplkitError, Exception)


def test_error_message():
    err = SmplkitError("something went wrong")
    assert str(err) == "something went wrong"
