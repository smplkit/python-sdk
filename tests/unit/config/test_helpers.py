"""Tests for config client helper functions."""

from http import HTTPStatus

import httpx
import pytest

from smplkit._errors import (
    ConflictError,
    ConnectionError,
    NotFoundError,
    TimeoutError,
    ValidationError,
)
from smplkit._generated.config.models.config_environments_type_0 import (
    ConfigEnvironmentsType0,
)
from smplkit._generated.config.models.config_item_definition import (
    ConfigItemDefinition,
)
from smplkit._generated.config.models.config_item_override import ConfigItemOverride
from smplkit._generated.config.models.config_items_type_0 import ConfigItemsType0
from smplkit._generated.config.models.environment_override import EnvironmentOverride
from smplkit._generated.config.models.environment_override_values_type_0 import (
    EnvironmentOverrideValuesType0,
)
from smplkit.config.client import (
    _check_response_status,
    _maybe_reraise_network_error,
)
from smplkit.config.helpers import (
    _build_config_request_body as _build_request_body,
    _extract_datetime,
    _extract_environments,
    _extract_items,
    _make_environments,
    _make_items,
    _unset_to_none,
)


class TestMakeItems:
    def test_none_returns_none(self):
        assert _make_items(None) is None

    def test_typed_shape_wraps_correctly(self):
        result = _make_items({"host": {"value": "localhost", "type": "STRING"}})
        assert isinstance(result, ConfigItemsType0)
        assert result.additional_properties["host"].value == "localhost"

    def test_plain_values_auto_wrapped(self):
        result = _make_items({"retries": 3})
        assert isinstance(result, ConfigItemsType0)
        assert result.additional_properties["retries"].value == 3


class TestMakeEnvironments:
    def test_none_returns_none(self):
        assert _make_environments(None) is None

    def test_dict_returns_environments_type(self):
        result = _make_environments({"prod": {"values": {"host": "db-prod"}}})
        assert isinstance(result, ConfigEnvironmentsType0)
        env_override = result.additional_properties["prod"]
        assert isinstance(env_override, EnvironmentOverride)
        assert env_override.values.additional_properties["host"].value == "db-prod"

    def test_already_wrapped_values(self):
        """Env values already in {value: raw} shape are unwrapped."""
        result = _make_environments({"prod": {"values": {"host": {"value": "db-prod"}}}})
        env_override = result.additional_properties["prod"]
        assert env_override.values.additional_properties["host"].value == "db-prod"

    def test_non_dict_env_data(self):
        """Non-dict env data creates an empty EnvironmentOverride."""
        result = _make_environments({"prod": "invalid"})
        env_override = result.additional_properties["prod"]
        assert isinstance(env_override, EnvironmentOverride)


class TestExtractItems:
    def test_none_returns_empty(self):
        assert _extract_items(None) == {}

    def test_dict_returns_copy(self):
        assert _extract_items({"a": 1}) == {"a": 1}

    def test_items_type_returns_typed_dict(self):
        obj = ConfigItemsType0()
        item = ConfigItemDefinition(value=42, type_="NUMBER", description="count")
        obj.additional_properties = {"x": item}
        result = _extract_items(obj)
        assert result["x"]["value"] == 42
        assert result["x"]["type"] == "NUMBER"
        assert result["x"]["description"] == "count"

    def test_unknown_type_returns_empty(self):
        assert _extract_items(42) == {}
        assert _extract_items("not a dict") == {}

    def test_unset_returns_empty(self):
        class Unset:
            pass

        assert _extract_items(Unset()) == {}


class TestExtractEnvironments:
    def test_none_returns_empty(self):
        assert _extract_environments(None) == {}

    def test_dict_returns_copy(self):
        assert _extract_environments({"prod": {}}) == {"prod": {}}

    def test_environments_type_returns_unwrapped_values(self):
        vals = EnvironmentOverrideValuesType0()
        vals.additional_properties = {"host": ConfigItemOverride(value="db-prod")}
        env_override = EnvironmentOverride(values=vals)
        obj = ConfigEnvironmentsType0()
        obj.additional_properties = {"staging": env_override}
        result = _extract_environments(obj)
        assert result["staging"]["values"] == {"host": "db-prod"}

    def test_unknown_type_returns_empty(self):
        assert _extract_environments(42) == {}
        assert _extract_environments("not a dict") == {}

    def test_unset_returns_empty(self):
        class Unset:
            pass

        assert _extract_environments(Unset()) == {}

    def test_plain_item_override_without_value_attr(self):
        """Override items without .value attribute are used as-is."""

        class PlainOverride:
            """Simulates an override without a .value attribute."""

            pass

        vals = EnvironmentOverrideValuesType0()
        vals.additional_properties = {"host": PlainOverride()}
        env_override = EnvironmentOverride(values=vals)
        obj = ConfigEnvironmentsType0()
        obj.additional_properties = {"prod": env_override}
        result = _extract_environments(obj)
        assert isinstance(result["prod"]["values"]["host"], PlainOverride)


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
        with pytest.raises(NotFoundError):
            _check_response_status(HTTPStatus.NOT_FOUND, b"Not Found")

    def test_409_raises_conflict(self):
        with pytest.raises(ConflictError):
            _check_response_status(HTTPStatus.CONFLICT, b"Conflict")

    def test_422_raises_validation(self):
        with pytest.raises(ValidationError):
            _check_response_status(HTTPStatus.UNPROCESSABLE_ENTITY, b"Validation Error")

    def test_200_does_not_raise(self):
        _check_response_status(HTTPStatus.OK, b"")  # Should not raise


class TestBuildRequestBody:
    def test_builds_valid_body(self):
        body = _build_request_body(
            name="Test",
            config_id="test",
            description="A test",
            items={"a": {"value": 1, "type": "NUMBER"}},
        )
        d = body.to_dict()
        assert d["data"]["attributes"]["name"] == "Test"
        assert d["data"]["id"] == "test"
        assert d["data"]["attributes"]["items"]["a"]["value"] == 1


class TestMaybeReraiseNetworkError:
    def test_timeout_exception(self):
        with pytest.raises(TimeoutError):
            _maybe_reraise_network_error(httpx.ReadTimeout("timed out"))

    def test_timeout_includes_url_when_available(self):
        exc = httpx.ReadTimeout("timed out")
        exc.request = httpx.Request("GET", "http://config.localhost/api/v1/configs")
        with pytest.raises(TimeoutError, match="http://config.localhost/api/v1/configs"):
            _maybe_reraise_network_error(exc)

    def test_connection_error(self):
        with pytest.raises(ConnectionError):
            _maybe_reraise_network_error(httpx.ConnectError("connection refused"))

    def test_connection_error_includes_url_when_available(self):
        exc = httpx.ConnectError("nodename nor servname provided, or not known")
        exc.request = httpx.Request("GET", "http://config.localhost/api/v1/configs")
        with pytest.raises(ConnectionError, match="http://config.localhost/api/v1/configs"):
            _maybe_reraise_network_error(exc)

    def test_connection_error_fallback_message_without_url(self):
        exc = httpx.ConnectError("nodename nor servname provided, or not known")
        with pytest.raises(ConnectionError, match="Connection error"):
            _maybe_reraise_network_error(exc)

    def test_connection_error_uses_base_url_when_request_not_attached(self):
        exc = httpx.ConnectError("nodename nor servname provided, or not known")
        with pytest.raises(ConnectionError, match="http://config.localhost"):
            _maybe_reraise_network_error(exc, "http://config.localhost")

    def test_timeout_uses_base_url_when_request_not_attached(self):
        exc = httpx.ReadTimeout("timed out")
        with pytest.raises(TimeoutError, match="http://config.localhost"):
            _maybe_reraise_network_error(exc, "http://config.localhost")

    def test_exc_url_takes_precedence_over_base_url(self):
        exc = httpx.ConnectError("refused")
        exc.request = httpx.Request("GET", "http://config.localhost/api/v1/configs")
        with pytest.raises(ConnectionError, match="http://config.localhost/api/v1/configs"):
            _maybe_reraise_network_error(exc, "http://other.host")

    def test_sdk_errors_reraise(self):
        with pytest.raises(NotFoundError):
            _maybe_reraise_network_error(NotFoundError("not found"))

        with pytest.raises(ConflictError):
            _maybe_reraise_network_error(ConflictError("conflict"))

        with pytest.raises(ValidationError):
            _maybe_reraise_network_error(ValidationError("invalid"))

    def test_other_exceptions_pass_through(self):
        # Should not raise — just returns
        _maybe_reraise_network_error(ValueError("unrelated"))
