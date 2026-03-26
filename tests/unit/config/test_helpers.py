"""Tests for config client helper functions."""

from http import HTTPStatus

import httpx
import pytest

from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit._generated.config.models.config_environments_type_0 import (
    ConfigEnvironmentsType0,
)
from smplkit._generated.config.models.config_values_type_0 import ConfigValuesType0
from smplkit.config.client import (
    _build_request_body,
    _check_response_status,
    _extract_datetime,
    _extract_environments,
    _extract_values,
    _make_environments,
    _make_values,
    _maybe_reraise_network_error,
    _unset_to_none,
)


class TestMakeValues:
    def test_none_returns_none(self):
        assert _make_values(None) is None

    def test_dict_returns_values_type(self):
        result = _make_values({"a": 1})
        assert isinstance(result, ConfigValuesType0)
        assert result.additional_properties == {"a": 1}


class TestMakeEnvironments:
    def test_none_returns_none(self):
        assert _make_environments(None) is None

    def test_dict_returns_environments_type(self):
        result = _make_environments({"prod": {"values": {}}})
        assert isinstance(result, ConfigEnvironmentsType0)


class TestExtractValues:
    def test_none_returns_empty(self):
        assert _extract_values(None) == {}

    def test_dict_returns_copy(self):
        assert _extract_values({"a": 1}) == {"a": 1}

    def test_values_type_returns_dict(self):
        obj = ConfigValuesType0()
        obj.additional_properties = {"x": 42}
        assert _extract_values(obj) == {"x": 42}

    def test_unknown_type_returns_empty(self):
        assert _extract_values(42) == {}
        assert _extract_values("not a dict") == {}


class TestExtractEnvironments:
    def test_none_returns_empty(self):
        assert _extract_environments(None) == {}

    def test_dict_returns_copy(self):
        assert _extract_environments({"prod": {}}) == {"prod": {}}

    def test_environments_type_returns_dict(self):
        obj = ConfigEnvironmentsType0()
        obj.additional_properties = {"staging": {"values": {}}}
        assert _extract_environments(obj) == {"staging": {"values": {}}}

    def test_unknown_type_returns_empty(self):
        assert _extract_environments(42) == {}
        assert _extract_environments("not a dict") == {}


class TestExtractDatetime:
    def test_none_returns_none(self):
        assert _extract_datetime(None) is None

    def test_passes_through_datetime(self):
        import datetime

        dt = datetime.datetime(2026, 1, 1)
        assert _extract_datetime(dt) is dt

    def test_unset_returns_none(self):
        class Unset:
            pass
        assert _extract_datetime(Unset()) is None


class TestUnsetToNone:
    def test_none_stays_none(self):
        assert _unset_to_none(None) is None

    def test_string_passes_through(self):
        assert _unset_to_none("hello") == "hello"

    def test_unset_returns_none(self):
        class Unset:
            pass
        assert _unset_to_none(Unset()) is None


class TestCheckResponseStatus:
    def test_404_raises_not_found(self):
        with pytest.raises(SmplNotFoundError):
            _check_response_status(HTTPStatus.NOT_FOUND, b"Not Found")

    def test_409_raises_conflict(self):
        with pytest.raises(SmplConflictError):
            _check_response_status(HTTPStatus.CONFLICT, b"Conflict")

    def test_422_raises_validation(self):
        with pytest.raises(SmplValidationError):
            _check_response_status(
                HTTPStatus.UNPROCESSABLE_ENTITY, b"Validation Error"
            )

    def test_200_does_not_raise(self):
        _check_response_status(HTTPStatus.OK, b"")  # Should not raise


class TestBuildRequestBody:
    def test_builds_valid_body(self):
        body = _build_request_body(
            name="Test",
            key="test",
            description="A test",
            values={"a": 1},
        )
        d = body.to_dict()
        assert d["data"]["attributes"]["name"] == "Test"
        assert d["data"]["attributes"]["key"] == "test"


class TestMaybeReraiseNetworkError:
    def test_timeout_exception(self):
        with pytest.raises(SmplTimeoutError):
            _maybe_reraise_network_error(httpx.ReadTimeout("timed out"))

    def test_connection_error(self):
        with pytest.raises(SmplConnectionError):
            _maybe_reraise_network_error(
                httpx.ConnectError("connection refused")
            )

    def test_sdk_errors_reraise(self):
        with pytest.raises(SmplNotFoundError):
            _maybe_reraise_network_error(SmplNotFoundError("not found"))

        with pytest.raises(SmplConflictError):
            _maybe_reraise_network_error(SmplConflictError("conflict"))

        with pytest.raises(SmplValidationError):
            _maybe_reraise_network_error(SmplValidationError("invalid"))

    def test_other_exceptions_pass_through(self):
        # Should not raise — just returns
        _maybe_reraise_network_error(ValueError("unrelated"))
