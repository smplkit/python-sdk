"""Tests for structured JSON:API error detail surfacing in SDK exceptions."""

from __future__ import annotations

import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import (
    ApiErrorDetail,
    SmplConflictError,
    SmplError,
    SmplNotFoundError,
    SmplValidationError,
    _derive_message,
    _parse_error_body,
    _raise_for_status,
)


# ---------------------------------------------------------------------------
# _parse_error_body
# ---------------------------------------------------------------------------


class TestParseErrorBody:
    def test_single_error(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/id"},
                    }
                ]
            }
        ).encode()
        errors = _parse_error_body(body)
        assert len(errors) == 1
        assert errors[0].status == "400"
        assert errors[0].title == "Validation Error"
        assert errors[0].detail == "The 'id' field is required."
        assert errors[0].source == {"pointer": "/data/id"}

    def test_multiple_errors(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'name' field is required.",
                        "source": {"pointer": "/data/attributes/name"},
                    },
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/id"},
                    },
                ]
            }
        ).encode()
        errors = _parse_error_body(body)
        assert len(errors) == 2

    def test_invalid_json(self):
        assert _parse_error_body(b"<html>Bad Gateway</html>") == []

    def test_empty_body(self):
        assert _parse_error_body(b"") == []

    def test_no_errors_key(self):
        assert _parse_error_body(json.dumps({"data": {}}).encode()) == []

    def test_partial_fields(self):
        body = json.dumps({"errors": [{"detail": "oops"}]}).encode()
        errors = _parse_error_body(body)
        assert len(errors) == 1
        assert errors[0].detail == "oops"
        assert errors[0].status is None
        assert errors[0].title is None
        assert errors[0].source == {}

    def test_non_dict_items_skipped(self):
        body = json.dumps({"errors": ["not-a-dict", {"detail": "real"}]}).encode()
        errors = _parse_error_body(body)
        assert len(errors) == 1
        assert errors[0].detail == "real"


# ---------------------------------------------------------------------------
# _derive_message
# ---------------------------------------------------------------------------


class TestDeriveMessage:
    def test_empty_list(self):
        assert _derive_message([]) == "An API error occurred"

    def test_detail_first(self):
        err = ApiErrorDetail(status="400", title="Bad Request", detail="Name is required.")
        assert _derive_message([err]) == "Name is required."

    def test_title_fallback(self):
        err = ApiErrorDetail(status="400", title="Bad Request")
        assert _derive_message([err]) == "Bad Request"

    def test_status_fallback(self):
        err = ApiErrorDetail(status="400")
        assert _derive_message([err]) == "400"

    def test_all_empty(self):
        err = ApiErrorDetail()
        assert _derive_message([err]) == "An API error occurred"

    def test_multiple_errors_suffix(self):
        errs = [ApiErrorDetail(detail="first"), ApiErrorDetail(detail="second")]
        assert _derive_message(errs) == "first (and 1 more error)"

    def test_three_errors_suffix(self):
        errs = [
            ApiErrorDetail(detail="a"),
            ApiErrorDetail(detail="b"),
            ApiErrorDetail(detail="c"),
        ]
        assert _derive_message(errs) == "a (and 2 more errors)"


# ---------------------------------------------------------------------------
# SmplError enhanced constructor and __str__
# ---------------------------------------------------------------------------


class TestSmplErrorStr:
    def test_single_error_str(self):
        err = SmplValidationError(
            "The 'id' field is required.",
            errors=[
                ApiErrorDetail(
                    status="400",
                    title="Validation Error",
                    detail="The 'id' field is required.",
                    source={"pointer": "/data/id"},
                )
            ],
            status_code=400,
        )
        s = str(err)
        assert "The 'id' field is required." in s
        assert "Error:" in s
        assert '"/data/id"' in s

    def test_multi_error_str(self):
        err = SmplValidationError(
            "The 'name' field is required. (and 1 more error)",
            errors=[
                ApiErrorDetail(
                    status="400",
                    title="Validation Error",
                    detail="The 'name' field is required.",
                    source={"pointer": "/data/attributes/name"},
                ),
                ApiErrorDetail(
                    status="400",
                    title="Validation Error",
                    detail="The 'id' field is required.",
                    source={"pointer": "/data/id"},
                ),
            ],
            status_code=400,
        )
        s = str(err)
        assert "Errors:" in s
        assert "[0]" in s
        assert "[1]" in s
        assert "The 'name' field is required." in s
        assert "The 'id' field is required." in s

    def test_no_errors_str(self):
        err = SmplError("plain message")
        assert str(err) == "plain message"
        assert err.errors == []
        assert err.status_code is None

    def test_backwards_compat_positional_message(self):
        err = SmplNotFoundError("Config abc not found")
        assert str(err) == "Config abc not found"
        assert err.errors == []

    def test_message_derived_when_none(self):
        err = SmplError(errors=[ApiErrorDetail(detail="auto-derived")])
        assert "auto-derived" in str(err)


# ---------------------------------------------------------------------------
# _raise_for_status
# ---------------------------------------------------------------------------


class TestRaiseForStatus:
    def test_2xx_no_raise(self):
        _raise_for_status(200, b"")
        _raise_for_status(201, b"")
        _raise_for_status(204, b"")

    def test_400_validation_error(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/id"},
                    }
                ]
            }
        ).encode()
        with pytest.raises(SmplValidationError) as exc_info:
            _raise_for_status(400, body)
        exc = exc_info.value
        assert exc.status_code == 400
        assert len(exc.errors) == 1
        assert exc.errors[0].detail == "The 'id' field is required."
        assert exc.errors[0].source == {"pointer": "/data/id"}
        assert "The 'id' field is required." in str(exc)
        assert '"/data/id"' in str(exc)

    def test_400_multi_error(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'name' field is required.",
                        "source": {"pointer": "/data/attributes/name"},
                    },
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/id"},
                    },
                ]
            }
        ).encode()
        with pytest.raises(SmplValidationError) as exc_info:
            _raise_for_status(400, body)
        exc = exc_info.value
        assert "(and 1 more error)" in str(exc)
        assert len(exc.errors) == 2
        assert "Errors:" in str(exc)
        assert "[0]" in str(exc)
        assert "[1]" in str(exc)

    def test_404_not_found(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "Config 'abc' does not exist.",
                    }
                ]
            }
        ).encode()
        with pytest.raises(SmplNotFoundError) as exc_info:
            _raise_for_status(404, body)
        exc = exc_info.value
        assert exc.status_code == 404
        assert "Config 'abc' does not exist." in str(exc)

    def test_409_conflict(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "409",
                        "title": "Conflict",
                        "detail": "Config has children and cannot be deleted.",
                    }
                ]
            }
        ).encode()
        with pytest.raises(SmplConflictError) as exc_info:
            _raise_for_status(409, body)
        exc = exc_info.value
        assert exc.status_code == 409
        assert "Config has children" in str(exc)

    def test_422_validation(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "422",
                        "title": "Unprocessable Entity",
                        "detail": "Invalid key format.",
                    }
                ]
            }
        ).encode()
        with pytest.raises(SmplValidationError) as exc_info:
            _raise_for_status(422, body)
        assert exc_info.value.status_code == 422

    def test_500_server_error(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "status": "500",
                        "title": "Internal Server Error",
                        "detail": "Something went wrong.",
                    }
                ]
            }
        ).encode()
        with pytest.raises(SmplError) as exc_info:
            _raise_for_status(500, body)
        exc = exc_info.value
        assert exc.status_code == 500
        assert "Something went wrong." in str(exc)

    def test_non_json_response(self):
        with pytest.raises(SmplError) as exc_info:
            _raise_for_status(502, b"<html>Bad Gateway</html>")
        exc = exc_info.value
        assert exc.status_code == 502
        assert "HTTP 502" in str(exc)
        assert exc.errors == []

    def test_empty_body(self):
        with pytest.raises(SmplError) as exc_info:
            _raise_for_status(502, b"")
        assert exc_info.value.status_code == 502
        assert exc_info.value.errors == []


# ---------------------------------------------------------------------------
# Integration: wrapper method raises structured errors
# ---------------------------------------------------------------------------


def _make_error_response(status_code: int, errors_body: dict) -> MagicMock:
    """Build a mock response matching the generated client's Response pattern."""
    resp = MagicMock()
    resp.status_code = HTTPStatus(status_code)
    resp.content = json.dumps(errors_body).encode()
    resp.parsed = None
    return resp


class TestConfigClientErrors:
    @patch("smplkit.config.client.update_config.sync_detailed")
    def test_update_config_400_surfaces_detail(self, mock_update):
        mock_update.return_value = _make_error_response(
            400,
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/id"},
                    }
                ]
            },
        )
        from smplkit.client import SmplClient
        from smplkit.config.models import Config

        import datetime

        client = SmplClient(api_key="sk_test", environment="test")
        cfg = Config(
            client.config,
            id="test",
            name="test",
            created_at=datetime.datetime(2025, 1, 1),
        )
        with pytest.raises(SmplValidationError) as exc_info:
            cfg.save()
        exc = exc_info.value
        assert exc.status_code == 400
        assert "The 'id' field is required." in str(exc)
        assert len(exc.errors) == 1
        assert exc.errors[0].source == {"pointer": "/data/id"}

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_create_config_multi_error(self, mock_create):
        mock_create.return_value = _make_error_response(
            400,
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'name' field is required.",
                        "source": {"pointer": "/data/attributes/name"},
                    },
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/id"},
                    },
                ]
            },
        )
        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        cfg = client.config.management.new("test-key", name="test")
        with pytest.raises(SmplValidationError) as exc_info:
            cfg.save()
        exc = exc_info.value
        assert len(exc.errors) == 2
        assert "(and 1 more error)" in str(exc)

    @patch("smplkit.config.client.get_config.sync_detailed")
    def test_get_config_404_surfaces_detail(self, mock_get):
        mock_get.return_value = _make_error_response(
            404,
            {
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "Config 'abc' does not exist.",
                    }
                ]
            },
        )
        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotFoundError) as exc_info:
            client.config.management.get("abc")
        exc = exc_info.value
        assert exc.status_code == 404
        assert "Config 'abc' does not exist." in str(exc)

    @patch("smplkit.config.client.delete_config.sync_detailed")
    def test_delete_config_409_surfaces_detail(self, mock_delete):
        mock_delete.return_value = _make_error_response(
            409,
            {
                "errors": [
                    {
                        "status": "409",
                        "title": "Conflict",
                        "detail": "Config has children and cannot be deleted.",
                    }
                ]
            },
        )
        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplConflictError) as exc_info:
            client.config.management.delete("test-config")
        exc = exc_info.value
        assert exc.status_code == 409
        assert "Config has children" in str(exc)

    @patch("smplkit.config.client.create_config.sync_detailed")
    def test_non_json_error_response(self, mock_create):
        resp = MagicMock()
        resp.status_code = HTTPStatus(502)
        resp.content = b"<html>Bad Gateway</html>"
        resp.parsed = None
        mock_create.return_value = resp

        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        cfg = client.config.management.new("test-key", name="test")
        with pytest.raises(SmplError) as exc_info:
            cfg.save()
        exc = exc_info.value
        assert exc.status_code == 502
        assert "HTTP 502" in str(exc)
        assert exc.errors == []


class TestFlagsClientErrors:
    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_flag_400_surfaces_detail(self, mock_create):
        mock_create.return_value = _make_error_response(
            400,
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'id' field is required.",
                        "source": {"pointer": "/data/attributes/id"},
                    }
                ]
            },
        )
        from smplkit.client import SmplClient
        from smplkit.flags.models import Flag

        client = SmplClient(api_key="sk_test", environment="test")
        flag = Flag(
            client.flags,
            id="test",
            name="Test",
            type="boolean",
            default=True,
        )
        with pytest.raises(SmplValidationError) as exc_info:
            flag.save()
        exc = exc_info.value
        assert exc.status_code == 400
        assert "The 'id' field is required." in str(exc)

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_flag_404_surfaces_detail(self, mock_get):
        mock_get.return_value = _make_error_response(
            404,
            {
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "Flag does not exist.",
                    }
                ]
            },
        )
        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotFoundError) as exc_info:
            client.flags.management.get("test-flag")
        exc = exc_info.value
        assert exc.status_code == 404
        assert "Flag does not exist." in str(exc)


class TestLoggingClientErrors:
    @patch("smplkit.logging.client.create_logger.sync_detailed")
    def test_create_logger_400_surfaces_detail(self, mock_create):
        mock_create.return_value = _make_error_response(
            400,
            {
                "errors": [
                    {
                        "status": "400",
                        "title": "Validation Error",
                        "detail": "The 'name' field is required.",
                        "source": {"pointer": "/data/attributes/name"},
                    }
                ]
            },
        )
        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        lg = client.logging.management.new("test-key", name="Test")
        with pytest.raises(SmplValidationError) as exc_info:
            lg.save()
        exc = exc_info.value
        assert exc.status_code == 400
        assert "The 'name' field is required." in str(exc)

    @patch("smplkit.logging.client.get_logger.sync_detailed")
    def test_get_logger_404_surfaces_detail(self, mock_get):
        mock_get.return_value = _make_error_response(
            404,
            {
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "Logger does not exist.",
                    }
                ]
            },
        )
        from smplkit.client import SmplClient

        client = SmplClient(api_key="sk_test", environment="test")
        with pytest.raises(SmplNotFoundError) as exc_info:
            client.logging.management.get("test-key")
        exc = exc_info.value
        assert exc.status_code == 404
        assert "Logger does not exist." in str(exc)


class TestApiErrorDetailSerialization:
    def test_to_dict_full(self):
        err = ApiErrorDetail(
            status="400",
            title="Validation Error",
            detail="Bad field.",
            source={"pointer": "/data/id"},
        )
        d = err.to_dict()
        assert d == {
            "status": "400",
            "title": "Validation Error",
            "detail": "Bad field.",
            "source": {"pointer": "/data/id"},
        }

    def test_to_dict_minimal(self):
        err = ApiErrorDetail(detail="oops")
        d = err.to_dict()
        assert d == {"detail": "oops"}

    def test_to_json(self):
        err = ApiErrorDetail(status="400", detail="oops")
        j = err.to_json()
        parsed = json.loads(j)
        assert parsed["status"] == "400"
        assert parsed["detail"] == "oops"
