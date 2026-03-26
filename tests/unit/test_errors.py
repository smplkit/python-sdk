"""Tests for SDK error types."""

from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)


def test_smpl_error_is_base():
    assert issubclass(SmplConnectionError, SmplError)
    assert issubclass(SmplTimeoutError, SmplError)
    assert issubclass(SmplNotFoundError, SmplError)
    assert issubclass(SmplConflictError, SmplError)
    assert issubclass(SmplValidationError, SmplError)


def test_smpl_error_is_exception():
    assert issubclass(SmplError, Exception)


def test_error_message():
    err = SmplError("something went wrong")
    assert str(err) == "something went wrong"
