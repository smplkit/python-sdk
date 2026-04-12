"""Tests for FlagsClient and AsyncFlagsClient — management + runtime."""

import asyncio
import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import pytest

from smplkit._errors import (
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit.client import AsyncSmplClient, SmplClient
from smplkit.flags.client import (
    AsyncFlagsClient,
    FlagChangeEvent,
    FlagsClient,
    FlagStats,
    _ContextRegistrationBuffer,
    _CONTEXT_REGISTRATION_LRU_SIZE,
    _ResolutionCache,
    _build_gen_flag,
    _build_request_body,
    _check_response_status,
    _contexts_to_eval_dict,
    _evaluate_flag,
    _extract_environments,
    _extract_rule,
    _extract_values,
    _flag_dict_from_json,
    _hash_context,
    _maybe_reraise_network_error,
    _unset_to_none,
)
from smplkit.flags.models import (
    AsyncBooleanFlag,
    AsyncFlag,
    AsyncJsonFlag,
    AsyncNumberFlag,
    AsyncStringFlag,
    BooleanFlag,
    Flag,
    JsonFlag,
    NumberFlag,
    StringFlag,
)
from smplkit.flags.types import Context

_TEST_UUID = "5a0c6be1-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _mock_flag_response(*, id=_TEST_UUID, name="Test Flag", type_="BOOLEAN", default=False):
    """Build a mock parsed flag response (single-resource envelope)."""
    mock_values = [MagicMock(name="True", value=True), MagicMock(name="False", value=False)]
    mock_values[0].name = "True"
    mock_values[0].value = True
    mock_values[1].name = "False"
    mock_values[1].value = False

    mock_attrs = MagicMock()
    mock_attrs.name = name
    mock_attrs.type_ = type_
    mock_attrs.default = default
    mock_attrs.values = mock_values
    mock_attrs.description = None
    mock_attrs.created_at = None
    mock_attrs.updated_at = None

    from smplkit._generated.flags.types import UNSET

    mock_attrs.environments = UNSET

    mock_resource = MagicMock()
    mock_resource.id = id
    mock_resource.attributes = mock_attrs

    mock_parsed = MagicMock()
    mock_parsed.data = mock_resource

    return mock_parsed


def _mock_list_parsed(*, id=_TEST_UUID, name="Test Flag", type_="BOOLEAN", default=False):
    """Build a mock parsed list response (array of resources)."""
    single = _mock_flag_response(id=id, name=name, type_=type_, default=default)
    mock_parsed = MagicMock()
    mock_parsed.data = [single.data]
    return mock_parsed


_UNSET = object()


def _flag_json(
    *,
    id=_TEST_UUID,
    name="Test Flag",
    type_="BOOLEAN",
    default=False,
    values=_UNSET,
    environments=None,
):
    """Build a raw JSON:API flag resource dict."""
    if values is _UNSET:
        values = [{"name": "True", "value": True}, {"name": "False", "value": False}]
    return {
        "id": id,
        "type": "flag",
        "attributes": {
            "name": name,
            "type": type_,
            "default": default,
            "values": values,
            "environments": environments or {},
            "description": "",
            "created_at": None,
            "updated_at": None,
        },
    }


def _ok_response(parsed=None, status=HTTPStatus.OK, content=None):
    """Build a mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = content if content is not None else b""
    resp.parsed = parsed
    return resp


def _ok_json_response(data, status=HTTPStatus.OK):
    """Build a mock HTTP response with JSON content (for raw-JSON parsing)."""
    content = json.dumps(data).encode()
    return _ok_response(status=status, content=content)


def _make_flags_client():
    """Create a FlagsClient with a mocked parent."""
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = None
    with patch("smplkit.flags.client.AuthenticatedClient"):
        client = FlagsClient(parent)
    return client


def _make_async_flags_client():
    """Create an AsyncFlagsClient with a mocked parent."""
    parent = MagicMock()
    parent._api_key = "sk_test"
    parent._environment = "test"
    parent._service = None
    with patch("smplkit.flags.client.AuthenticatedClient"):
        client = AsyncFlagsClient(parent)
    return client


def _make_mock_flag(client):
    """Create a Flag model for _update_flag tests."""
    return Flag(
        client,
        id=_TEST_UUID,
        name="Test Flag",
        type="BOOLEAN",
        default=False,
        values=[{"name": "True", "value": True}, {"name": "False", "value": False}],
    )


def _make_mock_async_flag(client):
    """Create an AsyncFlag model for _update_flag tests."""
    return AsyncFlag(
        client,
        id=_TEST_UUID,
        name="Test Flag",
        type="BOOLEAN",
        default=False,
        values=[{"name": "True", "value": True}, {"name": "False", "value": False}],
    )


# ===========================================================================
# Helper functions
# ===========================================================================


class TestCheckResponseStatus:
    def test_200_does_nothing(self):
        _check_response_status(200, b"ok")

    def test_404_raises_not_found(self):
        with pytest.raises(SmplNotFoundError):
            _check_response_status(404, b"not found")

    def test_422_raises_validation(self):
        with pytest.raises(SmplValidationError):
            _check_response_status(422, b"validation detail")


class TestMaybeReraiseNetworkError:
    def test_timeout_exception(self):
        with pytest.raises(SmplTimeoutError):
            _maybe_reraise_network_error(httpx.TimeoutException("timed out"))

    def test_connect_error(self):
        with pytest.raises(SmplConnectionError):
            _maybe_reraise_network_error(httpx.ConnectError("refused"))

    def test_reraises_not_found(self):
        with pytest.raises(SmplNotFoundError):
            _maybe_reraise_network_error(SmplNotFoundError("nope"))

    def test_reraises_validation(self):
        with pytest.raises(SmplValidationError):
            _maybe_reraise_network_error(SmplValidationError("bad"))

    def test_ignores_generic_exception(self):
        _maybe_reraise_network_error(ValueError("other"))


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
        class Unset:
            pass

        assert _extract_environments(Unset()) == {}

    def test_unknown_type_returns_empty(self):
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

    def test_rule_with_none_description(self):
        from smplkit._generated.flags.models.flag_rule import FlagRule
        from smplkit._generated.flags.models.flag_rule_logic import FlagRuleLogic

        logic = FlagRuleLogic()
        logic.additional_properties = {}
        rule = FlagRule(logic=logic, value=42, description=None)
        result = _extract_rule(rule)
        assert "description" not in result


class TestExtractValues:
    def test_empty_returns_empty(self):
        assert _extract_values([]) == []

    def test_none_returns_none(self):
        assert _extract_values(None) is None

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


class TestBuildGenFlag:
    def test_with_environments(self):
        result = _build_gen_flag(
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
        assert result.name == "Test"
        assert "production" in result.environments.additional_properties

    def test_without_environments(self):
        result = _build_gen_flag(
            name="Test",
            type_="STRING",
            default="off",
            values=[],
        )
        assert result.name == "Test"


class TestBuildRequestBody:
    def test_wraps_flag(self):
        gen_flag = _build_gen_flag(name="Test", type_="BOOLEAN", default=False, values=[])
        body = _build_request_body(gen_flag)
        assert body.data.attributes is gen_flag
        assert body.data.type_ == "flag"
        assert body.data.id is None

    def test_with_flag_id(self):
        gen_flag = _build_gen_flag(name="Test", type_="BOOLEAN", default=False, values=[])
        body = _build_request_body(gen_flag, flag_id="abc-123")
        assert body.data.id == "abc-123"


class TestFlagDictFromJson:
    def test_with_environments(self):
        data = {
            "id": "abc-123",
            "type": "flag",
            "attributes": {
                "name": "My Flag",
                "type": "STRING",
                "default": "hello",
                "values": None,
                "description": "A flag",
                "environments": {
                    "production": {
                        "enabled": True,
                        "default": "world",
                        "rules": [{"logic": {"op": "eq"}, "value": "x"}],
                    }
                },
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        }
        result = _flag_dict_from_json(data)
        assert result["id"] == "abc-123"
        assert result["values"] is None
        assert result["environments"]["production"]["enabled"] is True
        assert result["environments"]["production"]["default"] == "world"
        assert len(result["environments"]["production"]["rules"]) == 1


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
        result = _contexts_to_eval_dict([Context("device", "d-1", os="ios")])
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
        d2 = {"user": {"plan": "enterprise", "key": "u-1"}}
        assert _hash_context(d1) == _hash_context(d2)

    def test_different_input_different_hash(self):
        d1 = {"user": {"key": "u-1"}}
        d2 = {"user": {"key": "u-2"}}
        assert _hash_context(d1) != _hash_context(d2)


# ===========================================================================
# FlagChangeEvent
# ===========================================================================


class TestFlagChangeEvent:
    def test_construction(self):
        event = FlagChangeEvent(id="my-flag", source="websocket")
        assert event.id == "my-flag"
        assert event.source == "websocket"

    def test_repr(self):
        event = FlagChangeEvent(id="f", source="manual")
        assert "FlagChangeEvent" in repr(event)
        assert "f" in repr(event)


# ===========================================================================
# _ResolutionCache
# ===========================================================================


class TestResolutionCache:
    def test_put_and_get(self):
        cache = _ResolutionCache()
        cache.put("key1", "value1")
        hit, value = cache.get("key1")
        assert hit is True
        assert value == "value1"

    def test_miss(self):
        cache = _ResolutionCache()
        hit, value = cache.get("nonexistent")
        assert hit is False
        assert value is None

    def test_hit_miss_counters(self):
        cache = _ResolutionCache()
        cache.put("k", "v")
        cache.get("k")  # hit
        cache.get("k")  # hit
        cache.get("missing")  # miss
        assert cache.cache_hits == 2
        assert cache.cache_misses == 1

    def test_clear(self):
        cache = _ResolutionCache()
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.clear()
        hit, _ = cache.get("k1")
        assert hit is False

    def test_lru_eviction(self):
        cache = _ResolutionCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)
        hit_a, _ = cache.get("a")
        assert hit_a is False
        hit_b, _ = cache.get("b")
        assert hit_b is True

    def test_lru_access_refreshes(self):
        cache = _ResolutionCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # refreshes "a"
        cache.put("d", 4)  # evicts "b"
        hit_a, _ = cache.get("a")
        assert hit_a is True
        hit_b, _ = cache.get("b")
        assert hit_b is False

    def test_overwrite_existing(self):
        cache = _ResolutionCache()
        cache.put("k", "v1")
        cache.put("k", "v2")
        _, value = cache.get("k")
        assert value == "v2"


class TestFlagStats:
    def test_construction_and_repr(self):
        stats = FlagStats(cache_hits=10, cache_misses=5)
        assert stats.cache_hits == 10
        assert stats.cache_misses == 5
        assert "10" in repr(stats)
        assert "5" in repr(stats)


# ===========================================================================
# _ContextRegistrationBuffer
# ===========================================================================


class TestContextRegistrationBuffer:
    def test_observe_and_drain(self):
        buf = _ContextRegistrationBuffer()
        buf.observe([Context("user", "u-1", plan="enterprise"), Context("account", "a-1", region="us")])
        batch = buf.drain()
        assert len(batch) == 2
        assert batch[0]["type"] == "user"
        assert batch[0]["key"] == "u-1"
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_deduplication(self):
        buf = _ContextRegistrationBuffer()
        buf.observe([Context("user", "u-1", plan="enterprise")])
        buf.observe([Context("user", "u-1", plan="enterprise")])
        assert len(buf.drain()) == 1

    def test_drain_clears_pending(self):
        buf = _ContextRegistrationBuffer()
        buf.observe([Context("user", "u-1")])
        buf.drain()
        assert len(buf.drain()) == 0

    def test_pending_count(self):
        buf = _ContextRegistrationBuffer()
        assert buf.pending_count == 0
        buf.observe([Context("user", "u-1"), Context("account", "a-1")])
        assert buf.pending_count == 2
        buf.drain()
        assert buf.pending_count == 0

    def test_lru_eviction(self):
        buf = _ContextRegistrationBuffer()
        for i in range(_CONTEXT_REGISTRATION_LRU_SIZE + 1):
            buf.observe([Context("user", f"u-{i}")])
        assert len(buf._seen) == _CONTEXT_REGISTRATION_LRU_SIZE


# ===========================================================================
# _evaluate_flag
# ===========================================================================


class TestEvaluateFlag:
    def _make_flag(self, *, default, environments=None):
        return {
            "id": "test-flag",
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
        assert _evaluate_flag(flag, "staging", {"user": {"plan": "enterprise"}}) is True

    def test_no_rules_match_returns_env_default(self):
        flag = self._make_flag(
            default="flag-default",
            environments={
                "staging": {
                    "enabled": True,
                    "default": "env-default",
                    "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": "matched"}],
                }
            },
        )
        assert _evaluate_flag(flag, "staging", {"user": {"plan": "free"}}) == "env-default"

    def test_no_rules_match_no_env_default_returns_flag_default(self):
        flag = self._make_flag(
            default="flag-default",
            environments={
                "staging": {
                    "enabled": True,
                    "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": "matched"}],
                }
            },
        )
        assert _evaluate_flag(flag, "staging", {"user": {"plan": "free"}}) == "flag-default"

    def test_numeric_comparison(self):
        flag = self._make_flag(
            default=3,
            environments={
                "staging": {
                    "enabled": True,
                    "rules": [{"logic": {">": [{"var": "account.employee_count"}, 100]}, "value": 5}],
                }
            },
        )
        assert _evaluate_flag(flag, "staging", {"account": {"employee_count": 500}}) == 5

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
                        }
                    ],
                }
            },
        )
        assert _evaluate_flag(flag, "staging", {"user": {"plan": "enterprise"}, "account": {"region": "us"}}) is True
        assert _evaluate_flag(flag, "staging", {"user": {"plan": "enterprise"}, "account": {"region": "eu"}}) is False

    def test_none_environment_returns_flag_default(self):
        flag = self._make_flag(default="default-val")
        assert _evaluate_flag(flag, None, {}) == "default-val"

    def test_json_logic_error_returns_fallback(self):
        flag = self._make_flag(
            default="fallback",
            environments={
                "prod": {
                    "enabled": True,
                    "default": "env-default",
                    "rules": [{"logic": {"invalid_op": [1, 2]}, "value": "matched"}],
                }
            },
        )
        assert _evaluate_flag(flag, "prod", {}) == "env-default"

    def test_empty_logic_skipped(self):
        flag = self._make_flag(
            default="fallback",
            environments={
                "prod": {
                    "enabled": True,
                    "default": "env-default",
                    "rules": [{"logic": {}, "value": "never"}],
                }
            },
        )
        assert _evaluate_flag(flag, "prod", {}) == "env-default"


# ===========================================================================
# Sync FlagsClient: init
# ===========================================================================


class TestFlagsClientInit:
    def test_init(self):
        client = SmplClient(api_key="sk_test", environment="test")
        assert isinstance(client.flags, FlagsClient)


# ===========================================================================
# Sync FlagsClient: factory methods
# ===========================================================================


class TestFlagsClientFactoryMethods:
    def test_newBooleanFlag(self):
        client = _make_flags_client()
        flag = client.management.newBooleanFlag("checkout-v2", default=False)
        assert isinstance(flag, BooleanFlag)
        assert flag.id == "checkout-v2"
        assert flag.type == "BOOLEAN"
        assert flag.default is False
        assert flag.name == "Checkout V2"
        assert len(flag.values) == 2

    def test_newBooleanFlag_custom_name(self):
        client = _make_flags_client()
        flag = client.management.newBooleanFlag("my-flag", default=True, name="My Custom Name", description="desc")
        assert flag.name == "My Custom Name"
        assert flag.description == "desc"
        assert flag.default is True

    def test_newStringFlag(self):
        client = _make_flags_client()
        flag = client.management.newStringFlag("color-theme", default="light")
        assert isinstance(flag, StringFlag)
        assert flag.id == "color-theme"
        assert flag.type == "STRING"
        assert flag.default == "light"

    def test_newStringFlag_with_values(self):
        client = _make_flags_client()
        flag = client.management.newStringFlag(
            "plan", default="free", values=[{"name": "Free", "value": "free"}, {"name": "Pro", "value": "pro"}]
        )
        assert len(flag.values) == 2

    def test_newNumberFlag(self):
        client = _make_flags_client()
        flag = client.management.newNumberFlag("max-retries", default=3)
        assert isinstance(flag, NumberFlag)
        assert flag.id == "max-retries"
        assert flag.type == "NUMERIC"
        assert flag.default == 3

    def test_newJsonFlag(self):
        client = _make_flags_client()
        flag = client.management.newJsonFlag("config", default={"mode": "standard"})
        assert isinstance(flag, JsonFlag)
        assert flag.id == "config"
        assert flag.type == "JSON"
        assert flag.default == {"mode": "standard"}

    def test_newStringFlag_unconstrained(self):
        client = _make_flags_client()
        flag = client.management.newStringFlag("greeting", default="hello")
        assert flag.values is None
        assert flag.default == "hello"

    def test_newNumberFlag_unconstrained(self):
        client = _make_flags_client()
        flag = client.management.newNumberFlag("threshold", default=42)
        assert flag.values is None
        assert flag.default == 42

    def test_newJsonFlag_unconstrained(self):
        client = _make_flags_client()
        flag = client.management.newJsonFlag("settings", default={"a": 1})
        assert flag.values is None
        assert flag.default == {"a": 1}

    def test_newBooleanFlag_always_constrained(self):
        client = _make_flags_client()
        flag = client.management.newBooleanFlag("toggle", default=True)
        assert flag.values is not None
        assert len(flag.values) == 2


# ===========================================================================
# Sync FlagsClient: get(id), list(), delete(id)
# ===========================================================================


class TestFlagsClientCRUD:
    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_by_id(self, mock_get):
        mock_get.return_value = _ok_json_response({"data": _flag_json()})
        client = _make_flags_client()
        flag = client.management.get("test-flag")
        assert flag.id == _TEST_UUID
        mock_get.assert_called_once()

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_not_found(self, mock_get):
        mock_get.return_value = _ok_json_response({}, status=HTTPStatus.NOT_FOUND)
        client = _make_flags_client()
        with pytest.raises(SmplNotFoundError):
            client.management.get("test-flag")

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_network_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("refused")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client.management.get("test-flag")

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_timeout(self, mock_get):
        mock_get.side_effect = httpx.ReadTimeout("timed out")
        client = _make_flags_client()
        with pytest.raises(SmplTimeoutError):
            client.management.get("test-flag")

    @patch("smplkit.flags.client.get_flag.sync_detailed")
    def test_get_generic_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        with pytest.raises(RuntimeError):
            client.management.get("test-flag")

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        flags = client.management.list()
        assert len(flags) == 1
        assert flags[0].id == _TEST_UUID

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list_empty(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": []})
        client = _make_flags_client()
        assert client.management.list() == []

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client.management.list()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        with pytest.raises(RuntimeError):
            client.management.list()

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete_by_id(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)
        client = _make_flags_client()
        client.management.delete("test-flag")
        mock_delete.assert_called_once()

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete_not_found(self, mock_delete):
        mock_delete.return_value = _ok_json_response({}, status=HTTPStatus.NOT_FOUND)
        client = _make_flags_client()
        with pytest.raises(SmplNotFoundError):
            client.management.delete("test-flag")

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.ConnectError("refused")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client.management.delete("test-flag")

    @patch("smplkit.flags.client.delete_flag.sync_detailed")
    def test_delete_generic_exception(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        with pytest.raises(RuntimeError):
            client.management.delete("test-flag")


# ===========================================================================
# Sync FlagsClient: _create_flag, _update_flag
# ===========================================================================


class TestFlagsClientCreateUpdateFlag:
    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_flag_success(self, mock_create):
        mock_create.return_value = _ok_json_response({"data": _flag_json()}, status=HTTPStatus.CREATED)
        client = _make_flags_client()
        flag = Flag(client, id="new-flag", name="New", type="BOOLEAN", default=False)
        result = client._create_flag(flag)
        assert result.id == _TEST_UUID

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_flag_with_environments(self, mock_create):
        mock_create.return_value = _ok_json_response({"data": _flag_json()}, status=HTTPStatus.CREATED)
        client = _make_flags_client()
        flag = Flag(
            client,
            id="new-flag",
            name="New",
            type="BOOLEAN",
            default=False,
            environments={"staging": {"enabled": True, "rules": []}},
        )
        result = client._create_flag(flag)
        assert result.id == _TEST_UUID

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_flag_unconstrained(self, mock_create):
        mock_create.return_value = _ok_json_response(
            {"data": _flag_json(type_="STRING", default="hello", values=None)},
            status=HTTPStatus.CREATED,
        )
        client = _make_flags_client()
        flag = Flag(client, id="greeting", name="Greeting", type="STRING", default="hello", values=None)
        result = client._create_flag(flag)
        assert result.values is None
        assert result.default == "hello"

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_flag_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")
        client = _make_flags_client()
        flag = Flag(client, id="new-flag", name="New", type="BOOLEAN", default=False)
        with pytest.raises(SmplConnectionError):
            client._create_flag(flag)

    @patch("smplkit.flags.client.create_flag.sync_detailed")
    def test_create_flag_generic_exception(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        flag = Flag(client, id="new-flag", name="New", type="BOOLEAN", default=False)
        with pytest.raises(RuntimeError):
            client._create_flag(flag)

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_success(self, mock_update):
        mock_update.return_value = _ok_json_response({"data": _flag_json()})
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        result = client._update_flag(flag=flag)
        assert result.id == _TEST_UUID

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_with_environments(self, mock_update):
        mock_update.return_value = _ok_json_response({"data": _flag_json()})
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        flag.environments = {"prod": {"enabled": True, "default": False, "rules": []}}
        result = client._update_flag(flag=flag)
        assert result.id == _TEST_UUID

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        with pytest.raises(SmplConnectionError):
            client._update_flag(flag=flag)

    @patch("smplkit.flags.client.update_flag.sync_detailed")
    def test_update_flag_generic_exception(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        flag = _make_mock_flag(client)
        with pytest.raises(RuntimeError):
            client._update_flag(flag=flag)


# ===========================================================================
# Sync FlagsClient: typed flag handles (runtime)
# ===========================================================================


class TestFlagsClientTypedHandles:
    def test_booleanFlag(self):
        client = _make_flags_client()
        handle = client.booleanFlag("checkout-v2", default=False)
        assert isinstance(handle, BooleanFlag)
        assert handle.id == "checkout-v2"
        assert handle.default is False
        assert "checkout-v2" in client._handles

    def test_stringFlag(self):
        client = _make_flags_client()
        handle = client.stringFlag("color", default="red")
        assert isinstance(handle, StringFlag)
        assert handle.id == "color"
        assert handle.default == "red"

    def test_numberFlag(self):
        client = _make_flags_client()
        handle = client.numberFlag("retries", default=3)
        assert isinstance(handle, NumberFlag)
        assert handle.id == "retries"
        assert handle.default == 3

    def test_jsonFlag(self):
        client = _make_flags_client()
        handle = client.jsonFlag("config", default={"a": 1})
        assert isinstance(handle, JsonFlag)
        assert handle.id == "config"
        assert handle.default == {"a": 1}


# ===========================================================================
# Sync FlagsClient: on_change dual-mode decorator
# ===========================================================================


class TestFlagsClientOnChange:
    def test_bare_decorator(self):
        client = _make_flags_client()

        @client.on_change
        def listener(event):
            pass

        assert len(client._global_listeners) == 1
        assert client._global_listeners[0] is listener

    def test_key_scoped_decorator(self):
        client = _make_flags_client()

        @client.on_change("my-flag")
        def listener(event):
            pass

        assert "my-flag" in client._key_listeners
        assert len(client._key_listeners["my-flag"]) == 1
        assert client._key_listeners["my-flag"][0] is listener

    def test_empty_parens_decorator(self):
        client = _make_flags_client()

        @client.on_change()
        def listener(event):
            pass

        assert len(client._global_listeners) == 1
        assert client._global_listeners[0] is listener


# ===========================================================================
# Sync FlagsClient: context provider
# ===========================================================================


class TestFlagsClientContextProvider:
    def test_context_provider_decorator(self):
        client = _make_flags_client()

        @client.context_provider
        def provider():
            return [Context("user", "u-1")]

        assert client._context_provider is provider


# ===========================================================================
# Sync FlagsClient: connect / refresh / stats
# ===========================================================================


class TestFlagsClientLifecycle:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_connect_internal(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        client._parent._environment = "staging"
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws

        client._connect_internal()

        assert client._connected is True
        assert client._environment == "staging"
        assert client._ws_manager is mock_ws
        assert mock_ws.on.call_count == 2
        assert _TEST_UUID in client._flag_store

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_connect_internal_idempotent(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        client._parent._environment = "staging"
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws

        client._connect_internal()
        client._connect_internal()

        assert mock_list.call_count == 1

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_refresh(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        client._connected = True
        client._flag_store = {"old-flag": {"id": "old-flag"}}
        listener = MagicMock()
        client._global_listeners.append(listener)

        client.refresh()

        assert _TEST_UUID in client._flag_store
        assert listener.called

    def test_stats(self):
        client = _make_flags_client()
        stats = client.stats()
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0


# ===========================================================================
# Sync FlagsClient: register / flush
# ===========================================================================


class TestFlagsClientRegisterFlush:
    def test_register_single(self):
        client = _make_flags_client()
        client.register(Context("user", "u-1", plan="enterprise"))
        batch = client._context_buffer.drain()
        assert len(batch) == 1
        assert batch[0]["type"] == "user"

    def test_register_list(self):
        client = _make_flags_client()
        client.register([Context("user", "u-1"), Context("account", "acme")])
        batch = client._context_buffer.drain()
        assert len(batch) == 2

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_with_pending(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_flags_client()
        client.register(Context("user", "u-1", plan="enterprise"))
        client.flush_contexts()
        mock_bulk.assert_called_once()
        _, kwargs = mock_bulk.call_args
        body = kwargs["body"]
        assert body.contexts[0].type_ == "user"

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_empty_batch(self, mock_bulk):
        client = _make_flags_client()
        client.flush_contexts()
        mock_bulk.assert_not_called()

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_exception_swallowed(self, mock_bulk):
        mock_bulk.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        client.register(Context("user", "u-1"))
        client.flush_contexts()  # should not raise

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_with_attributes(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_flags_client()
        client.register(Context("user", "u-1", plan="enterprise"))
        client.flush_contexts()
        _, kwargs = mock_bulk.call_args
        body = kwargs["body"]
        assert body.contexts[0].attributes is not None

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_without_attributes(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_flags_client()
        client.register(Context("user", "u-1"))
        client.flush_contexts()
        mock_bulk.assert_called_once()


# ===========================================================================
# Sync FlagsClient: _evaluate_handle (lazy init)
# ===========================================================================


class TestFlagsClientEvaluateHandle:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_lazy_connects_on_first_call(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        client._parent._environment = "staging"
        client._parent._service = None
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws

        client._evaluate_handle("test-flag", "default", None)
        assert client._connected is True
        assert client._ws_manager is mock_ws

    def test_with_explicit_context(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": False,
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True}],
                    },
                },
            }
        }
        result = client._evaluate_handle("flag-a", False, [Context("user", "u-1", plan="enterprise")])
        assert result is True

    def test_with_context_provider(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "off",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        client._context_provider = lambda: [Context("user", "u-1", plan="free")]

        result = client._evaluate_handle("flag-a", "off", None)
        assert result == "off"
        assert client._context_buffer.pending_count > 0

    @patch("smplkit.flags.client.threading.Thread")
    def test_context_provider_triggers_flush_when_buffer_full(self, mock_thread):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {"flag-a": {"id": "flag-a", "default": False, "environments": {}}}

        for i in range(100):
            client._context_buffer.observe([Context("user", f"u-{i}")])

        client._context_provider = lambda: [Context("user", "trigger")]
        client._evaluate_handle("flag-a", False, None)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    def test_no_provider_empty_context(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "fallback",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        result = client._evaluate_handle("flag-a", "fallback", None)
        assert result == "fallback"

    def test_flag_not_in_store_returns_default(self):
        client = _make_flags_client()
        client._connected = True
        client._parent._service = None
        client._flag_store = {}
        result = client._evaluate_handle("missing", "default_val", [Context("user", "u-1")])
        assert result == "default_val"

    def test_evaluate_none_becomes_default(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {"flag-a": {"id": "flag-a", "default": None, "environments": {}}}
        result = client._evaluate_handle("flag-a", "my-default", [Context("user", "u-1")])
        assert result == "my-default"

    def test_cache_hit(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "val",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        ctx = [Context("user", "u-1")]
        client._evaluate_handle("flag-a", "val", ctx)
        result = client._evaluate_handle("flag-a", "val", ctx)
        assert result == "val"
        assert client._cache.cache_hits == 1
        assert client._cache.cache_misses == 1

    def test_service_context_injected(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = "my-svc"
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "fallback",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        # Call with no explicit context, no provider
        client._evaluate_handle("flag-a", "fallback", None)
        # Verify cache key includes the service context
        assert client._cache.cache_misses == 1

    def test_service_context_not_overridden_by_explicit(self):
        client = _make_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = "my-svc"
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "fallback",
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [{"logic": {"==": [{"var": "service.key"}, "custom-svc"]}, "value": "matched"}],
                    },
                },
            }
        }
        # Service key already in explicit context should not be overridden
        ctx = [Context("service", "custom-svc")]
        result = client._evaluate_handle("flag-a", "fallback", ctx)
        assert result == "matched"


# ===========================================================================
# Sync FlagsClient: Event handlers + change listeners
# ===========================================================================


class TestFlagsClientEventHandlers:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_flag_changed({"id": "test-flag"})
        mock_list.assert_called_once()
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed_fetch_error_propagates(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client._handle_flag_changed({"id": "test-flag"})

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_flag_deleted({"id": "test-flag"})
        mock_list.assert_called_once()
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted_fetch_error_propagates(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client._handle_flag_deleted({"id": "test-flag"})


class TestFlagsClientChangeListeners:
    def test_fire_global_and_key_scoped(self):
        client = _make_flags_client()
        global_listener = MagicMock()
        key_listener = MagicMock()
        client._global_listeners.append(global_listener)
        client._key_listeners["my-flag"] = [key_listener]

        client._fire_change_listeners("my-flag", "websocket")

        global_listener.assert_called_once()
        key_listener.assert_called_once()

    def test_global_listener_exception_swallowed(self):
        client = _make_flags_client()
        bad = MagicMock(side_effect=RuntimeError("boom"))
        good = MagicMock()
        client._global_listeners.extend([bad, good])
        client._fire_change_listeners("flag-a", "websocket")
        good.assert_called_once()

    def test_key_listener_exception_swallowed(self):
        client = _make_flags_client()
        bad = MagicMock(side_effect=RuntimeError("boom"))
        client._key_listeners["flag-a"] = [bad]
        # Should not raise
        client._fire_change_listeners("flag-a", "websocket")

    def test_none_key_fires_nothing(self):
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._fire_change_listeners(None, "websocket")
        listener.assert_not_called()

    def test_fire_change_listeners_all(self):
        client = _make_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._flag_store = {"flag-a": {"id": "flag-a"}, "flag-b": {"id": "flag-b"}}
        client._fire_change_listeners_all("manual")
        assert listener.call_count == 2


# ===========================================================================
# Sync FlagsClient: Model conversion
# ===========================================================================


class TestFlagsClientModelConversion:
    def test_to_model(self):
        client = _make_flags_client()
        parsed = _mock_flag_response()
        result = client._to_model(parsed)
        assert isinstance(result, Flag)
        assert result.id == _TEST_UUID

    def test_resource_to_model(self):
        client = _make_flags_client()
        resource = _mock_flag_response().data
        result = client._resource_to_model(resource)
        assert isinstance(result, Flag)
        assert result.id == _TEST_UUID
        assert result.name == "Test Flag"


# ===========================================================================
# Sync FlagsClient: Fetch internals
# ===========================================================================


class TestFlagsClientFetchInternals:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_all_flags(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        client._fetch_all_flags()
        assert _TEST_UUID in client._flag_store

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_flags_client()
        result = client._fetch_flags_list()
        assert len(result) == 1
        assert result[0]["id"] == _TEST_UUID

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list_empty(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": []})
        client = _make_flags_client()
        assert client._fetch_flags_list() == []

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_flags_client()
        with pytest.raises(SmplConnectionError):
            client._fetch_flags_list()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_flags_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = _make_flags_client()
        with pytest.raises(RuntimeError):
            client._fetch_flags_list()


# ===========================================================================
# Sync FlagsClient: runtime integration
# ===========================================================================


class TestFlagsClientRuntimeIntegration:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_get_with_connected_store(self, mock_list):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns._connected = True
        ns._environment = "staging"
        ns._flag_store = {
            "checkout-v2": {
                "id": "checkout-v2",
                "default": False,
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True}],
                    },
                },
            },
        }
        handle = ns.booleanFlag("checkout-v2", default=False)
        assert handle.get(context=[Context("user", "u-1", plan="enterprise")]) is True
        assert handle.get(context=[Context("user", "u-2", plan="free")]) is False

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_cache_hits_on_repeated_evaluation(self, mock_list):
        client = SmplClient(api_key="sk_test", environment="test")
        ns = client.flags
        ns._connected = True
        ns._environment = "staging"
        ns._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": False,
                "environments": {"staging": {"enabled": True, "rules": []}},
            },
        }
        handle = ns.booleanFlag("flag-a", default=False)
        ctx = [Context("user", "u-1", plan="free")]
        handle.get(context=ctx)
        handle.get(context=ctx)
        handle.get(context=ctx)
        stats = ns.stats()
        assert stats.cache_misses == 1
        assert stats.cache_hits == 2


# ===========================================================================
# AsyncFlagsClient: init
# ===========================================================================


class TestAsyncFlagsClientInit:
    def test_init(self):
        client = AsyncSmplClient(api_key="sk_test", environment="test")
        assert isinstance(client.flags, AsyncFlagsClient)


# ===========================================================================
# AsyncFlagsClient: factory methods
# ===========================================================================


class TestAsyncFlagsClientFactoryMethods:
    def test_newBooleanFlag(self):
        client = _make_async_flags_client()
        flag = client.management.newBooleanFlag("checkout-v2", default=False)
        assert isinstance(flag, AsyncBooleanFlag)
        assert flag.id == "checkout-v2"
        assert flag.type == "BOOLEAN"
        assert flag.default is False

    def test_newBooleanFlag_custom_name(self):
        client = _make_async_flags_client()
        flag = client.management.newBooleanFlag("my-flag", default=True, name="Custom", description="desc")
        assert flag.name == "Custom"
        assert flag.description == "desc"

    def test_newStringFlag(self):
        client = _make_async_flags_client()
        flag = client.management.newStringFlag("color", default="red")
        assert isinstance(flag, AsyncStringFlag)
        assert flag.type == "STRING"

    def test_newStringFlag_with_values(self):
        client = _make_async_flags_client()
        flag = client.management.newStringFlag("plan", default="free", values=[{"name": "Free", "value": "free"}])
        assert len(flag.values) == 1

    def test_newNumberFlag(self):
        client = _make_async_flags_client()
        flag = client.management.newNumberFlag("retries", default=3)
        assert isinstance(flag, AsyncNumberFlag)
        assert flag.type == "NUMERIC"

    def test_newJsonFlag(self):
        client = _make_async_flags_client()
        flag = client.management.newJsonFlag("config", default={"a": 1})
        assert isinstance(flag, AsyncJsonFlag)
        assert flag.type == "JSON"

    def test_newStringFlag_unconstrained(self):
        client = _make_async_flags_client()
        flag = client.management.newStringFlag("greeting", default="hello")
        assert flag.values is None

    def test_newNumberFlag_unconstrained(self):
        client = _make_async_flags_client()
        flag = client.management.newNumberFlag("threshold", default=42)
        assert flag.values is None

    def test_newBooleanFlag_always_constrained(self):
        client = _make_async_flags_client()
        flag = client.management.newBooleanFlag("toggle", default=True)
        assert flag.values is not None
        assert len(flag.values) == 2


# ===========================================================================
# AsyncFlagsClient: get(id), list(), delete(id)
# ===========================================================================


class TestAsyncFlagsClientCRUD:
    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_by_id(self, mock_get):
        mock_get.return_value = _ok_json_response({"data": _flag_json()})

        async def _run():
            client = _make_async_flags_client()
            flag = await client.management.get("test-flag")
            assert flag.id == _TEST_UUID
            mock_get.assert_called_once()

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_not_found(self, mock_get):
        mock_get.return_value = _ok_json_response({}, status=HTTPStatus.NOT_FOUND)

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplNotFoundError):
                await client.management.get("test-flag")

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_network_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplConnectionError):
                await client.management.get("test-flag")

        asyncio.run(_run())

    @patch("smplkit.flags.client.get_flag.asyncio_detailed")
    def test_get_generic_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError):
                await client.management.get("test-flag")

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})

        async def _run():
            client = _make_async_flags_client()
            flags = await client.management.list()
            assert len(flags) == 1

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list_empty(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": []})

        async def _run():
            client = _make_async_flags_client()
            assert await client.management.list() == []

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list_empty_no_data_attr(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": []})

        async def _run():
            client = _make_async_flags_client()
            assert await client.management.list() == []

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplConnectionError):
                await client.management.list()

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError):
                await client.management.list()

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete_by_id(self, mock_delete):
        mock_delete.return_value = _ok_response(status=HTTPStatus.NO_CONTENT)

        async def _run():
            client = _make_async_flags_client()
            await client.management.delete("test-flag")
            mock_delete.assert_called_once()

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete_not_found(self, mock_delete):
        mock_delete.return_value = _ok_json_response({}, status=HTTPStatus.NOT_FOUND)

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplNotFoundError):
                await client.management.delete("test-flag")

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete_network_error(self, mock_delete):
        mock_delete.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplConnectionError):
                await client.management.delete("test-flag")

        asyncio.run(_run())

    @patch("smplkit.flags.client.delete_flag.asyncio_detailed")
    def test_delete_generic_exception(self, mock_delete):
        mock_delete.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError):
                await client.management.delete("test-flag")

        asyncio.run(_run())


# ===========================================================================
# AsyncFlagsClient: _create_flag, _update_flag
# ===========================================================================


class TestAsyncFlagsClientCreateUpdateFlag:
    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_flag_success(self, mock_create):
        mock_create.return_value = _ok_json_response({"data": _flag_json()}, status=HTTPStatus.CREATED)

        async def _run():
            client = _make_async_flags_client()
            flag = AsyncFlag(client, id="new", name="New", type="BOOLEAN", default=False)
            result = await client._create_flag(flag)
            assert result.id == _TEST_UUID

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_flag_network_error(self, mock_create):
        mock_create.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = _make_async_flags_client()
            flag = AsyncFlag(client, id="new", name="New", type="BOOLEAN", default=False)
            with pytest.raises(SmplConnectionError):
                await client._create_flag(flag)

        asyncio.run(_run())

    @patch("smplkit.flags.client.create_flag.asyncio_detailed")
    def test_create_flag_generic_exception(self, mock_create):
        mock_create.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            flag = AsyncFlag(client, id="new", name="New", type="BOOLEAN", default=False)
            with pytest.raises(RuntimeError):
                await client._create_flag(flag)

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_success(self, mock_update):
        mock_update.return_value = _ok_json_response({"data": _flag_json()})

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            result = await client._update_flag(flag=flag)
            assert result.id == _TEST_UUID

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_network_error(self, mock_update):
        mock_update.side_effect = httpx.ConnectError("refused")

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            with pytest.raises(SmplConnectionError):
                await client._update_flag(flag=flag)

        asyncio.run(_run())

    @patch("smplkit.flags.client.update_flag.asyncio_detailed")
    def test_update_flag_generic_exception(self, mock_update):
        mock_update.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            flag = _make_mock_async_flag(client)
            with pytest.raises(RuntimeError):
                await client._update_flag(flag=flag)

        asyncio.run(_run())


# ===========================================================================
# AsyncFlagsClient: typed flag handles
# ===========================================================================


class TestAsyncFlagsClientTypedHandles:
    def test_booleanFlag(self):
        client = _make_async_flags_client()
        handle = client.booleanFlag("test", default=False)
        assert isinstance(handle, AsyncBooleanFlag)
        assert handle.id == "test"
        assert "test" in client._handles

    def test_stringFlag(self):
        client = _make_async_flags_client()
        handle = client.stringFlag("color", default="red")
        assert isinstance(handle, AsyncStringFlag)
        assert handle.id == "color"

    def test_numberFlag(self):
        client = _make_async_flags_client()
        handle = client.numberFlag("retries", default=3)
        assert isinstance(handle, AsyncNumberFlag)
        assert handle.id == "retries"

    def test_jsonFlag(self):
        client = _make_async_flags_client()
        handle = client.jsonFlag("config", default={"a": 1})
        assert isinstance(handle, AsyncJsonFlag)
        assert handle.id == "config"


# ===========================================================================
# AsyncFlagsClient: on_change dual-mode decorator
# ===========================================================================


class TestAsyncFlagsClientOnChange:
    def test_bare_decorator(self):
        client = _make_async_flags_client()

        @client.on_change
        def listener(event):
            pass

        assert len(client._global_listeners) == 1

    def test_key_scoped_decorator(self):
        client = _make_async_flags_client()

        @client.on_change("my-flag")
        def listener(event):
            pass

        assert "my-flag" in client._key_listeners

    def test_empty_parens_decorator(self):
        client = _make_async_flags_client()

        @client.on_change()
        def listener(event):
            pass

        assert len(client._global_listeners) == 1


# ===========================================================================
# AsyncFlagsClient: context provider
# ===========================================================================


class TestAsyncFlagsClientContextProvider:
    def test_context_provider_decorator(self):
        client = _make_async_flags_client()

        @client.context_provider
        def provider():
            return [Context("user", "u-1")]

        assert client._context_provider is provider


# ===========================================================================
# AsyncFlagsClient: lifecycle
# ===========================================================================


class TestAsyncFlagsClientLifecycle:
    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_connect_internal(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})

        async def _run():
            client = _make_async_flags_client()
            client._parent._environment = "staging"
            mock_ws = MagicMock()
            client._parent._ensure_ws.return_value = mock_ws
            await client._connect_internal()
            assert client._connected is True
            assert client._environment == "staging"
            assert client._ws_manager is mock_ws
            assert mock_ws.on.call_count == 2

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_connect_internal_idempotent(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})

        async def _run():
            client = _make_async_flags_client()
            client._parent._environment = "staging"
            mock_ws = MagicMock()
            client._parent._ensure_ws.return_value = mock_ws
            await client._connect_internal()
            await client._connect_internal()
            assert mock_list.call_count == 1

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_refresh(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})

        async def _run():
            client = _make_async_flags_client()
            client._connected = True
            client._flag_store = {"old-flag": {"id": "old-flag"}}
            listener = MagicMock()
            client._global_listeners.append(listener)
            await client.refresh()
            assert _TEST_UUID in client._flag_store
            assert listener.called

        asyncio.run(_run())

    def test_stats(self):
        client = _make_async_flags_client()
        stats = client.stats()
        assert stats.cache_hits == 0


# ===========================================================================
# AsyncFlagsClient: register / flush
# ===========================================================================


class TestAsyncFlagsClientRegisterFlush:
    def test_register_single(self):
        client = _make_async_flags_client()
        client.register(Context("user", "u-1", plan="enterprise"))
        batch = client._context_buffer.drain()
        assert len(batch) == 1

    def test_register_list(self):
        client = _make_async_flags_client()
        client.register([Context("user", "u-1"), Context("account", "acme")])
        batch = client._context_buffer.drain()
        assert len(batch) == 2

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_flush_with_pending(self, mock_bulk):
        mock_bulk.return_value = _ok_response()

        async def _run():
            client = _make_async_flags_client()
            client.register(Context("user", "u-1"))
            await client.flush_contexts()
            mock_bulk.assert_called_once()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_flush_empty_batch(self, mock_bulk):
        async def _run():
            client = _make_async_flags_client()
            await client.flush_contexts()
            mock_bulk.assert_not_called()

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.asyncio_detailed")
    def test_flush_exception_swallowed(self, mock_bulk):
        mock_bulk.side_effect = httpx.ConnectError("fail")

        async def _run():
            client = _make_async_flags_client()
            client.register(Context("user", "u-1"))
            await client.flush_contexts()  # should not raise

        asyncio.run(_run())

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_contexts_bg(self, mock_bulk):
        mock_bulk.return_value = _ok_response()
        client = _make_async_flags_client()
        client.register(Context("user", "u-1"))
        client._flush_contexts_bg()
        mock_bulk.assert_called_once()

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_contexts_bg_empty(self, mock_bulk):
        client = _make_async_flags_client()
        client._flush_contexts_bg()
        mock_bulk.assert_not_called()

    @patch("smplkit.flags.client.gen_bulk_register_contexts.sync_detailed")
    def test_flush_contexts_bg_exception_swallowed(self, mock_bulk):
        mock_bulk.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        client.register(Context("user", "u-1"))
        client._flush_contexts_bg()  # should not raise


# ===========================================================================
# AsyncFlagsClient: _evaluate_handle (lazy init)
# ===========================================================================


class TestAsyncFlagsClientEvaluateHandle:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_lazy_connects_on_first_call(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_async_flags_client()
        client._parent._environment = "staging"
        client._parent._service = None
        mock_ws = MagicMock()
        client._parent._ensure_ws.return_value = mock_ws

        client._evaluate_handle("test-flag", "default", None)
        assert client._connected is True
        assert client._ws_manager is mock_ws

    def test_with_explicit_context(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": False,
                "environments": {
                    "staging": {
                        "enabled": True,
                        "rules": [{"logic": {"==": [{"var": "user.plan"}, "enterprise"]}, "value": True}],
                    },
                },
            }
        }
        result = client._evaluate_handle("flag-a", False, [Context("user", "u-1", plan="enterprise")])
        assert result is True

    def test_with_context_provider(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "off",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        client._context_provider = lambda: [Context("user", "u-1")]
        result = client._evaluate_handle("flag-a", "off", None)
        assert result == "off"
        assert client._context_buffer.pending_count > 0

    @patch("smplkit.flags.client.threading.Thread")
    def test_context_provider_triggers_flush(self, mock_thread):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {"flag-a": {"id": "flag-a", "default": False, "environments": {}}}
        for i in range(100):
            client._context_buffer.observe([Context("user", f"u-{i}")])
        client._context_provider = lambda: [Context("user", "trigger")]
        client._evaluate_handle("flag-a", False, None)
        mock_thread.assert_called_once()

    def test_no_provider_empty_context(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "fallback",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        assert client._evaluate_handle("flag-a", "fallback", None) == "fallback"

    def test_flag_not_in_store(self):
        client = _make_async_flags_client()
        client._connected = True
        client._parent._service = None
        client._flag_store = {}
        assert client._evaluate_handle("missing", "default_val", [Context("user", "u-1")]) == "default_val"

    def test_evaluate_none_becomes_default(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {"flag-a": {"id": "flag-a", "default": None, "environments": {}}}
        assert client._evaluate_handle("flag-a", "my-default", [Context("user", "u-1")]) == "my-default"

    def test_cache_hit(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = None
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "val",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        ctx = [Context("user", "u-1")]
        client._evaluate_handle("flag-a", "val", ctx)
        client._evaluate_handle("flag-a", "val", ctx)
        assert client._cache.cache_hits == 1

    def test_service_context_injected(self):
        client = _make_async_flags_client()
        client._connected = True
        client._environment = "staging"
        client._parent._service = "my-svc"
        client._flag_store = {
            "flag-a": {
                "id": "flag-a",
                "default": "fallback",
                "environments": {"staging": {"enabled": True, "rules": []}},
            }
        }
        client._evaluate_handle("flag-a", "fallback", None)
        assert client._cache.cache_misses == 1


# ===========================================================================
# AsyncFlagsClient: Event handlers
# ===========================================================================


class TestAsyncFlagsClientEventHandlers:
    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_flag_changed({"id": "test-flag"})
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_changed_fetch_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        client._handle_flag_changed({"id": "test-flag"})

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._handle_flag_deleted({"id": "test-flag"})
        listener.assert_called_once()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_handle_flag_deleted_fetch_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        client._handle_flag_deleted({"id": "test-flag"})


class TestAsyncFlagsClientChangeListeners:
    def test_fire_global_and_key_scoped(self):
        client = _make_async_flags_client()
        global_listener = MagicMock()
        key_listener = MagicMock()
        client._global_listeners.append(global_listener)
        client._key_listeners["my-flag"] = [key_listener]
        client._fire_change_listeners("my-flag", "websocket")
        global_listener.assert_called_once()
        key_listener.assert_called_once()

    def test_global_listener_exception_swallowed(self):
        client = _make_async_flags_client()
        bad = MagicMock(side_effect=RuntimeError("boom"))
        good = MagicMock()
        client._global_listeners.extend([bad, good])
        client._fire_change_listeners("flag-a", "websocket")
        good.assert_called_once()

    def test_key_listener_exception_swallowed(self):
        client = _make_async_flags_client()
        bad = MagicMock(side_effect=RuntimeError("boom"))
        client._key_listeners["flag-a"] = [bad]
        client._fire_change_listeners("flag-a", "websocket")

    def test_none_key_fires_nothing(self):
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._fire_change_listeners(None, "websocket")
        listener.assert_not_called()

    def test_fire_change_listeners_all(self):
        client = _make_async_flags_client()
        listener = MagicMock()
        client._global_listeners.append(listener)
        client._flag_store = {"a": {"id": "a"}, "b": {"id": "b"}}
        client._fire_change_listeners_all("manual")
        assert listener.call_count == 2


# ===========================================================================
# AsyncFlagsClient: Model conversion + fetch internals
# ===========================================================================


class TestAsyncFlagsClientInternals:
    def test_to_model(self):
        client = _make_async_flags_client()
        parsed = _mock_flag_response()
        result = client._to_model(parsed)
        assert isinstance(result, AsyncFlag)
        assert result.id == _TEST_UUID

    def test_resource_to_model(self):
        client = _make_async_flags_client()
        resource = _mock_flag_response().data
        result = client._resource_to_model(resource)
        assert isinstance(result, AsyncFlag)
        assert result.id == _TEST_UUID

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_all_flags(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})

        async def _run():
            client = _make_async_flags_client()
            await client._fetch_all_flags()
            assert _TEST_UUID in client._flag_store

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})

        async def _run():
            client = _make_async_flags_client()
            result = await client._fetch_flags_list()
            assert len(result) == 1
            assert result[0]["id"] == _TEST_UUID

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list_empty(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": []})

        async def _run():
            client = _make_async_flags_client()
            assert await client._fetch_flags_list() == []

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(SmplConnectionError):
                await client._fetch_flags_list()

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.asyncio_detailed")
    def test_fetch_flags_list_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")

        async def _run():
            client = _make_async_flags_client()
            with pytest.raises(RuntimeError):
                await client._fetch_flags_list()

        asyncio.run(_run())

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_all_flags_sync(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": [_flag_json()]})
        client = _make_async_flags_client()
        client._fetch_all_flags_sync()
        assert _TEST_UUID in client._flag_store

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_all_flags_sync_empty(self, mock_list):
        mock_list.return_value = _ok_json_response({"data": []})
        client = _make_async_flags_client()
        client._fetch_all_flags_sync()
        assert client._flag_store == {}

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_all_flags_sync_network_error(self, mock_list):
        mock_list.side_effect = httpx.ConnectError("fail")
        client = _make_async_flags_client()
        with pytest.raises(SmplConnectionError):
            client._fetch_all_flags_sync()

    @patch("smplkit.flags.client.list_flags.sync_detailed")
    def test_fetch_all_flags_sync_generic_exception(self, mock_list):
        mock_list.side_effect = RuntimeError("unexpected")
        client = _make_async_flags_client()
        with pytest.raises(RuntimeError, match="unexpected"):
            client._fetch_all_flags_sync()
