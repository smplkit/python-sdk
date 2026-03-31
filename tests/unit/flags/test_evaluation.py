"""Tests for context conversion and local JSON Logic evaluation."""

from smplkit.flags.client import _contexts_to_eval_dict, _evaluate_flag, _hash_context
from smplkit.flags.types import Context


class TestContextsToEvalDict:
    def test_basic_conversion(self):
        contexts = [
            Context("user", "u-123", plan="enterprise"),
            Context("account", "acme", region="us"),
        ]
        result = _contexts_to_eval_dict(contexts)
        assert result == {
            "user": {"key": "u-123", "plan": "enterprise"},
            "account": {"key": "acme", "region": "us"},
        }

    def test_key_injected(self):
        contexts = [Context("device", "d-1", os="ios")]
        result = _contexts_to_eval_dict(contexts)
        assert result["device"]["key"] == "d-1"
        assert result["device"]["os"] == "ios"

    def test_empty_list(self):
        assert _contexts_to_eval_dict([]) == {}

    def test_no_attributes(self):
        result = _contexts_to_eval_dict([Context("user", "u-1")])
        assert result == {"user": {"key": "u-1"}}


class TestHashContext:
    def test_same_input_same_hash(self):
        d1 = {"user": {"key": "u-1", "plan": "enterprise"}}
        d2 = {"user": {"plan": "enterprise", "key": "u-1"}}  # different order
        assert _hash_context(d1) == _hash_context(d2)

    def test_different_input_different_hash(self):
        d1 = {"user": {"key": "u-1"}}
        d2 = {"user": {"key": "u-2"}}
        assert _hash_context(d1) != _hash_context(d2)


class TestEvaluateFlag:
    """Test _evaluate_flag following ADR-022 §2.6 semantics."""

    def _make_flag(self, *, default, environments=None):
        return {
            "key": "test-flag",
            "name": "Test",
            "type": "BOOLEAN",
            "default": default,
            "values": [],
            "environments": environments or {},
        }

    def test_no_environment_returns_flag_default(self):
        flag = self._make_flag(default=False)
        assert _evaluate_flag(flag, "staging", {}) is False

    def test_environment_not_found_returns_flag_default(self):
        flag = self._make_flag(default="red", environments={"production": {"enabled": True, "rules": []}})
        assert _evaluate_flag(flag, "staging", {}) == "red"

    def test_disabled_returns_env_default(self):
        flag = self._make_flag(
            default=False,
            environments={"staging": {"enabled": False, "default": True, "rules": []}},
        )
        assert _evaluate_flag(flag, "staging", {}) is True

    def test_disabled_no_env_default_returns_flag_default(self):
        flag = self._make_flag(
            default="fallback",
            environments={"staging": {"enabled": False, "rules": []}},
        )
        assert _evaluate_flag(flag, "staging", {}) == "fallback"

    def test_first_matching_rule_wins(self):
        flag = self._make_flag(
            default=False,
            environments={
                "staging": {
                    "enabled": True,
                    "rules": [
                        {"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True},
                        {"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": False},
                    ],
                }
            },
        )
        ctx = {"user": {"plan": "enterprise"}}
        assert _evaluate_flag(flag, "staging", ctx) is True

    def test_no_rules_match_returns_env_default(self):
        flag = self._make_flag(
            default="flag-default",
            environments={
                "staging": {
                    "enabled": True,
                    "default": "env-default",
                    "rules": [
                        {"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": "matched"},
                    ],
                }
            },
        )
        ctx = {"user": {"plan": "free"}}
        assert _evaluate_flag(flag, "staging", ctx) == "env-default"

    def test_no_rules_match_no_env_default_returns_flag_default(self):
        flag = self._make_flag(
            default="flag-default",
            environments={
                "staging": {
                    "enabled": True,
                    "rules": [
                        {"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": "matched"},
                    ],
                }
            },
        )
        ctx = {"user": {"plan": "free"}}
        assert _evaluate_flag(flag, "staging", ctx) == "flag-default"

    def test_numeric_comparison(self):
        flag = self._make_flag(
            default=3,
            environments={
                "staging": {
                    "enabled": True,
                    "rules": [
                        {"logic": {">": [{"var": "account.employee_count"}, 100]}, "value": 5},
                    ],
                }
            },
        )
        ctx = {"account": {"employee_count": 500}}
        assert _evaluate_flag(flag, "staging", ctx) == 5

    def test_and_condition(self):
        flag = self._make_flag(
            default=False,
            environments={
                "staging": {
                    "enabled": True,
                    "rules": [
                        {
                            "logic": {
                                "and": [
                                    {"==": [{"var": "user.plan"}, "enterprise"]},
                                    {"==": [{"var": "account.region"}, "us"]},
                                ]
                            },
                            "value": True,
                        },
                    ],
                }
            },
        )
        # Both conditions match
        ctx = {"user": {"plan": "enterprise"}, "account": {"region": "us"}}
        assert _evaluate_flag(flag, "staging", ctx) is True

        # Only one matches
        ctx2 = {"user": {"plan": "enterprise"}, "account": {"region": "eu"}}
        assert _evaluate_flag(flag, "staging", ctx2) is False

    def test_none_environment_returns_flag_default(self):
        flag = self._make_flag(default="default-val")
        assert _evaluate_flag(flag, None, {}) == "default-val"
