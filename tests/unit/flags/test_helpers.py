"""Tests for helper functions, FlagChangeEvent, and remaining uncovered code."""

from unittest.mock import MagicMock, patch

import pytest

from smplkit._errors import SmplConflictError, SmplNotFoundError, SmplValidationError
from smplkit.flags.client import (
    FlagChangeEvent,
    FlagsClient,
    _ContextRegistrationBuffer,
    _CONTEXT_REGISTRATION_LRU_SIZE,
    _FlagHandle,
    _build_gen_flag,
    _check_response_status,
    _evaluate_flag,
    _extract_environments,
    _extract_rule,
    _extract_values,
    _maybe_reraise_network_error,
    _unset_to_none,
)
from smplkit.flags.types import Context


# ---------------------------------------------------------------------------
# _check_response_status
# ---------------------------------------------------------------------------


class TestCheckResponseStatus:
    def test_409_raises_conflict(self):
        with pytest.raises(SmplConflictError):
            _check_response_status(409, b"conflict detail")

    def test_422_raises_validation(self):
        with pytest.raises(SmplValidationError):
            _check_response_status(422, b"validation detail")

    def test_200_does_nothing(self):
        _check_response_status(200, b"ok")


# ---------------------------------------------------------------------------
# _maybe_reraise_network_error
# ---------------------------------------------------------------------------


class TestMaybeReraiseNetworkError:
    def test_reraises_not_found(self):
        with pytest.raises(SmplNotFoundError):
            _maybe_reraise_network_error(SmplNotFoundError("nope"))

    def test_reraises_validation(self):
        with pytest.raises(SmplValidationError):
            _maybe_reraise_network_error(SmplValidationError("bad"))

    def test_ignores_generic_exception(self):
        _maybe_reraise_network_error(ValueError("other"))


# ---------------------------------------------------------------------------
# _extract_environments / _extract_rule / _extract_values / _unset_to_none
# ---------------------------------------------------------------------------


class TestExtractEnvironments:
    def test_none_returns_empty(self):
        assert _extract_environments(None) == {}

    def test_dict_passthrough(self):
        d = {"prod": {"enabled": True}}
        assert _extract_environments(d) == d

    def test_unset_returns_empty(self):
        from smplkit._generated.flags.types import UNSET

        assert _extract_environments(UNSET) == {}

    def test_unset_by_type_name(self):
        """Cover line 89: type_name == 'Unset' fallback check."""

        class Unset:
            pass

        assert _extract_environments(Unset()) == {}

    def test_unknown_type_returns_empty(self):
        """Cover line 108: fallthrough return for unknown type."""
        assert _extract_environments(42) == {}

    def test_gen_flag_environments(self):
        from smplkit._generated.flags.models.flag_environment import FlagEnvironment
        from smplkit._generated.flags.models.flag_environments import FlagEnvironments
        from smplkit._generated.flags.models.flag_rule import FlagRule
        from smplkit._generated.flags.models.flag_rule_logic import FlagRuleLogic

        logic = FlagRuleLogic()
        logic.additional_properties = {"==": [{"var": "user.plan"}, "enterprise"]}
        rule = FlagRule(logic=logic, value=True, description="test rule")
        env = FlagEnvironment(enabled=True, default=False, rules=[rule])
        envs = FlagEnvironments()
        envs.additional_properties = {"production": env}

        result = _extract_environments(envs)
        assert "production" in result
        assert result["production"]["enabled"] is True
        assert result["production"]["default"] is False
        assert len(result["production"]["rules"]) == 1
        assert result["production"]["rules"][0]["description"] == "test rule"

    def test_gen_flag_environments_unset_fields(self):
        from smplkit._generated.flags.models.flag_environment import FlagEnvironment
        from smplkit._generated.flags.models.flag_environments import FlagEnvironments
        from smplkit._generated.flags.types import UNSET

        env = FlagEnvironment(enabled=UNSET, default=UNSET, rules=UNSET)
        envs = FlagEnvironments()
        envs.additional_properties = {"staging": env}

        result = _extract_environments(envs)
        assert "staging" in result
        assert result["staging"]["rules"] == []


class TestExtractRule:
    def test_basic_rule(self):
        from smplkit._generated.flags.models.flag_rule import FlagRule
        from smplkit._generated.flags.models.flag_rule_logic import FlagRuleLogic

        logic = FlagRuleLogic()
        logic.additional_properties = {"==": [1, 1]}
        rule = FlagRule(logic=logic, value="enabled", description="always on")
        result = _extract_rule(rule)
        assert result["logic"] == {"==": [1, 1]}
        assert result["value"] == "enabled"
        assert result["description"] == "always on"

    def test_rule_without_description(self):
        from smplkit._generated.flags.models.flag_rule import FlagRule
        from smplkit._generated.flags.models.flag_rule_logic import FlagRuleLogic
        from smplkit._generated.flags.types import UNSET

        logic = FlagRuleLogic()
        logic.additional_properties = {}
        rule = FlagRule(logic=logic, value=42, description=UNSET)
        result = _extract_rule(rule)
        assert "description" not in result


class TestExtractValues:
    def test_empty_returns_empty(self):
        assert _extract_values([]) == []
        assert _extract_values(None) == []

    def test_extracts_values(self):
        v1 = MagicMock()
        v1.name = "On"
        v1.value = True
        result = _extract_values([v1])
        assert result == [{"name": "On", "value": True}]


class TestUnsetToNone:
    def test_none_passthrough(self):
        assert _unset_to_none(None) is None

    def test_string_passthrough(self):
        assert _unset_to_none("hello") == "hello"

    def test_unset_becomes_none(self):
        from smplkit._generated.flags.types import UNSET

        assert _unset_to_none(UNSET) is None


# ---------------------------------------------------------------------------
# _build_gen_flag
# ---------------------------------------------------------------------------


class TestBuildGenFlag:
    def test_with_environments(self):
        result = _build_gen_flag(
            key="test",
            name="Test",
            type_="BOOLEAN",
            default=False,
            values=[{"name": "True", "value": True}],
            environments={
                "production": {
                    "enabled": True,
                    "default": False,
                    "rules": [{"logic": {"==": [1, 1]}, "value": True, "description": "always"}],
                }
            },
        )
        assert result.key == "test"
        assert "production" in result.environments.additional_properties

    def test_without_environments(self):
        result = _build_gen_flag(
            key="test",
            name="Test",
            type_="STRING",
            default="off",
            values=[],
        )
        assert result.key == "test"


# ---------------------------------------------------------------------------
# FlagChangeEvent
# ---------------------------------------------------------------------------


class TestFlagChangeEvent:
    def test_construction(self):
        event = FlagChangeEvent(key="my-flag", source="websocket")
        assert event.key == "my-flag"
        assert event.source == "websocket"

    def test_repr(self):
        event = FlagChangeEvent(key="f", source="manual")
        assert "FlagChangeEvent" in repr(event)
        assert "f" in repr(event)


# ---------------------------------------------------------------------------
# _FlagHandle base class
# ---------------------------------------------------------------------------


class TestFlagHandleBase:
    def test_base_get(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = 42
        handle = _FlagHandle(ns, "test", 0)
        assert handle.get() == 42


# ---------------------------------------------------------------------------
# _ContextRegistrationBuffer LRU eviction
# ---------------------------------------------------------------------------


class TestContextBufferLRU:
    def test_lru_eviction(self):
        buf = _ContextRegistrationBuffer()
        # Fill beyond LRU size
        for i in range(_CONTEXT_REGISTRATION_LRU_SIZE + 1):
            buf.observe([Context("user", f"u-{i}")])
        # The seen dict should be capped
        assert len(buf._seen) == _CONTEXT_REGISTRATION_LRU_SIZE


# ---------------------------------------------------------------------------
# FlagsClient handle factories (via mock parent)
# ---------------------------------------------------------------------------


class TestFlagsClientHandleFactories:
    def _make_client(self):
        parent = MagicMock()
        parent._api_key = "test-key"
        with patch("smplkit.flags.client.AuthenticatedClient"):
            return FlagsClient(parent)

    def test_string_flag(self):
        client = self._make_client()
        handle = client.stringFlag("color", "red")
        assert handle.key == "color"
        assert handle.default == "red"

    def test_number_flag(self):
        client = self._make_client()
        handle = client.numberFlag("retries", 3)
        assert handle.key == "retries"
        assert handle.default == 3

    def test_json_flag(self):
        client = self._make_client()
        handle = client.jsonFlag("config", {"a": 1})
        assert handle.key == "config"

    def test_connection_status_disconnected(self):
        client = self._make_client()
        assert client.connection_status() == "disconnected"


# ---------------------------------------------------------------------------
# _evaluate_flag edge cases
# ---------------------------------------------------------------------------


class TestEvaluateFlagEdgeCases:
    def test_json_logic_error_returns_fallback(self):
        flag_def = {
            "key": "test",
            "default": "fallback",
            "environments": {
                "prod": {
                    "enabled": True,
                    "default": "env-default",
                    "rules": [{"logic": {"invalid_op": [1, 2]}, "value": "matched"}],
                }
            },
        }
        result = _evaluate_flag(flag_def, "prod", {})
        # Invalid logic should be caught, fall through to env default
        assert result == "env-default"

    def test_empty_logic_skipped(self):
        """Cover line 1420: empty logic dict causes continue."""
        flag_def = {
            "key": "test",
            "default": "fallback",
            "environments": {
                "prod": {
                    "enabled": True,
                    "default": "env-default",
                    "rules": [{"logic": {}, "value": "never"}],
                }
            },
        }
        result = _evaluate_flag(flag_def, "prod", {})
        assert result == "env-default"


# ---------------------------------------------------------------------------
# Context.__repr__
# ---------------------------------------------------------------------------


class TestContextRepr:
    def test_repr(self):
        ctx = Context("user", "u-1", name="Alice", plan="enterprise")
        r = repr(ctx)
        assert "user" in r
        assert "u-1" in r
        assert "Alice" in r
