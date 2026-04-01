"""Tests for FlagType, Context, and Rule public types."""

from smplkit.flags.types import Context, FlagType, Rule


class TestFlagType:
    def test_values(self):
        assert FlagType.BOOLEAN == "BOOLEAN"
        assert FlagType.STRING == "STRING"
        assert FlagType.NUMERIC == "NUMERIC"
        assert FlagType.JSON == "JSON"

    def test_is_str_enum(self):
        assert isinstance(FlagType.BOOLEAN, str)


class TestContext:
    def test_kwargs_only(self):
        ctx = Context("user", "u-1", plan="enterprise", beta=True)
        assert ctx.type == "user"
        assert ctx.key == "u-1"
        assert ctx.attributes == {"plan": "enterprise", "beta": True}

    def test_dict_only(self):
        ctx = Context("account", "a-1", {"region": "us", "size": 100})
        assert ctx.type == "account"
        assert ctx.key == "a-1"
        assert ctx.attributes == {"region": "us", "size": 100}

    def test_mixed_dict_and_kwargs(self):
        ctx = Context("user", "u-1", {"plan": "free"}, plan="enterprise", extra="val")
        assert ctx.attributes["plan"] == "enterprise"  # kwargs win
        assert ctx.attributes["extra"] == "val"

    def test_no_attributes(self):
        ctx = Context("device", "d-1")
        assert ctx.attributes == {}

    def test_none_attributes(self):
        ctx = Context("device", "d-1", None)
        assert ctx.attributes == {}

    def test_name_keyword_only(self):
        ctx = Context("user", "u-1", name="Alice Smith", plan="enterprise")
        assert ctx.name == "Alice Smith"
        assert ctx.attributes == {"plan": "enterprise"}

    def test_name_defaults_to_none(self):
        ctx = Context("user", "u-1")
        assert ctx.name is None


class TestRule:
    def test_single_when(self):
        result = Rule("test rule").when("user.plan", "==", "enterprise").serve(True).build()
        assert result == {
            "description": "test rule",
            "logic": {"==": [{"var": "user.plan"}, "enterprise"]},
            "value": True,
        }

    def test_multiple_when_and(self):
        result = (
            Rule("two conditions")
            .when("user.plan", "==", "enterprise")
            .when("account.region", "==", "us")
            .serve(True)
            .build()
        )
        assert result["logic"] == {
            "and": [
                {"==": [{"var": "user.plan"}, "enterprise"]},
                {"==": [{"var": "account.region"}, "us"]},
            ]
        }

    def test_environment(self):
        result = Rule("env rule").environment("staging").when("x", "==", 1).serve("yes").build()
        assert result["environment"] == "staging"
        assert result["description"] == "env rule"
        assert result["value"] == "yes"

    def test_no_environment(self):
        result = Rule("no env").when("x", "==", 1).serve("v").build()
        assert "environment" not in result

    def test_operators(self):
        ops = ["==", "!=", ">", "<", ">=", "<=", "in"]
        for op in ops:
            result = Rule("op test").when("x", op, 42).serve(True).build()
            assert op in result["logic"]

    def test_contains_operator(self):
        result = Rule("contains").when("user.email", "contains", "@acme.com").serve(True).build()
        assert result["logic"] == {"in": ["@acme.com", {"var": "user.email"}]}

    def test_no_conditions(self):
        result = Rule("empty").serve("val").build()
        assert result["logic"] == {}

    def test_numeric_value(self):
        result = Rule("num").when("x", ">", 100).serve(5).build()
        assert result["value"] == 5

    def test_json_value(self):
        val = {"mode": "dark", "accent": "#000"}
        result = Rule("json").when("x", "==", "y").serve(val).build()
        assert result["value"] == val
