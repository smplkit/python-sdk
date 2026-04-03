"""Tests for logging client helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock

from smplkit._generated.logging.models.logger_environments_type_0 import LoggerEnvironmentsType0
from smplkit._generated.logging.models.log_group_environments_type_0 import LogGroupEnvironmentsType0
from smplkit._generated.logging.types import UNSET
from smplkit.logging.client import (
    _check_response_status,
    _extract_datetime,
    _extract_environments,
    _extract_sources,
    _make_environments,
    _make_group_environments,
    _unset_to_none,
    _build_logger_body,
    _build_group_body,
    _maybe_reraise_network_error,
    SmplLogger,
    SmplLogGroup,
)
from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)

import datetime
import httpx
import pytest
from http import HTTPStatus


class TestUnsetToNone:
    def test_none_stays_none(self):
        assert _unset_to_none(None) is None

    def test_unset_becomes_none(self):
        assert _unset_to_none(UNSET) is None

    def test_value_passes_through(self):
        assert _unset_to_none("hello") == "hello"


class TestExtractDatetime:
    def test_none(self):
        assert _extract_datetime(None) is None

    def test_unset(self):
        assert _extract_datetime(UNSET) is None

    def test_datetime(self):
        dt = datetime.datetime(2026, 1, 1)
        assert _extract_datetime(dt) is dt


class TestExtractEnvironments:
    def test_none(self):
        assert _extract_environments(None) == {}

    def test_unset(self):
        assert _extract_environments(UNSET) == {}

    def test_logger_environments_type(self):
        obj = LoggerEnvironmentsType0()
        obj.additional_properties = {"prod": {"level": "ERROR"}}
        assert _extract_environments(obj) == {"prod": {"level": "ERROR"}}

    def test_log_group_environments_type(self):
        obj = LogGroupEnvironmentsType0()
        obj.additional_properties = {"staging": {"level": "DEBUG"}}
        assert _extract_environments(obj) == {"staging": {"level": "DEBUG"}}

    def test_dict(self):
        assert _extract_environments({"prod": {"level": "WARN"}}) == {"prod": {"level": "WARN"}}

    def test_unknown_type(self):
        assert _extract_environments(42) == {}


class TestMakeEnvironments:
    def test_none(self):
        assert _make_environments(None) is None

    def test_dict(self):
        result = _make_environments({"prod": {"level": "ERROR"}})
        assert isinstance(result, LoggerEnvironmentsType0)
        assert result.additional_properties == {"prod": {"level": "ERROR"}}


class TestMakeGroupEnvironments:
    def test_none(self):
        assert _make_group_environments(None) is None

    def test_dict(self):
        result = _make_group_environments({"prod": {"level": "WARN"}})
        assert isinstance(result, LogGroupEnvironmentsType0)
        assert result.additional_properties == {"prod": {"level": "WARN"}}


class TestExtractSources:
    def test_none(self):
        assert _extract_sources(None) == []

    def test_unset(self):
        assert _extract_sources(UNSET) == []

    def test_list_with_additional_properties(self):
        item = MagicMock()
        item.additional_properties = {"service": "api", "first_observed": "2026-01-01"}
        result = _extract_sources([item])
        assert result == [{"service": "api", "first_observed": "2026-01-01"}]

    def test_list_with_dict(self):
        result = _extract_sources([{"service": "api"}])
        assert result == [{"service": "api"}]

    def test_not_list(self):
        assert _extract_sources(42) == []


class TestCheckResponseStatus:
    def test_404(self):
        with pytest.raises(SmplNotFoundError):
            _check_response_status(HTTPStatus.NOT_FOUND, b"not found")

    def test_409(self):
        with pytest.raises(SmplConflictError):
            _check_response_status(HTTPStatus.CONFLICT, b"conflict")

    def test_422(self):
        with pytest.raises(SmplValidationError):
            _check_response_status(HTTPStatus.UNPROCESSABLE_ENTITY, b"bad data")

    def test_200_ok(self):
        _check_response_status(HTTPStatus.OK, b"")

    def test_201_created(self):
        _check_response_status(HTTPStatus.CREATED, b"")


class TestMaybeReraiseNetworkError:
    def test_timeout(self):
        with pytest.raises(SmplTimeoutError):
            _maybe_reraise_network_error(httpx.ReadTimeout("timed out"))

    def test_http_error(self):
        with pytest.raises(SmplConnectionError):
            _maybe_reraise_network_error(httpx.ConnectError("refused"))

    def test_not_found_error(self):
        with pytest.raises(SmplNotFoundError):
            _maybe_reraise_network_error(SmplNotFoundError("nope"))

    def test_conflict_error(self):
        with pytest.raises(SmplConflictError):
            _maybe_reraise_network_error(SmplConflictError("conflict"))

    def test_validation_error(self):
        with pytest.raises(SmplValidationError):
            _maybe_reraise_network_error(SmplValidationError("bad"))

    def test_other_error_passes_through(self):
        # Should not raise; caller raises separately
        _maybe_reraise_network_error(ValueError("unrelated"))


class TestBuildLoggerBody:
    def test_basic(self):
        body = _build_logger_body(name="SQL Logger", key="sql")
        assert body.data.attributes.name == "SQL Logger"
        assert body.data.attributes.key == "sql"

    def test_with_environments(self):
        body = _build_logger_body(
            name="Test", key="t", environments={"prod": {"level": "ERROR"}}
        )
        assert body.data.attributes.environments is not None


class TestBuildGroupBody:
    def test_basic(self):
        body = _build_group_body(name="DB Loggers", key="db")
        assert body.data.attributes.name == "DB Loggers"
        assert body.data.attributes.key == "db"


class TestSmplLoggerRepr:
    def test_repr(self):
        lg = SmplLogger(id="1", key="sql", name="SQL Logger")
        assert "sql" in repr(lg)


class TestSmplLogGroupRepr:
    def test_repr(self):
        grp = SmplLogGroup(id="1", key="db", name="DB Loggers")
        assert "db" in repr(grp)
