"""Public types for the Flags SDK: FlagType, Context, Rule."""

from __future__ import annotations

from enum import Enum
from typing import Any


class FlagType(str, Enum):
    """The value type of a flag."""

    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    NUMERIC = "NUMERIC"
    JSON = "JSON"


class Context:
    """A typed evaluation context entity.

    Represents a single entity (user, account, device, etc.) in the
    evaluation context.  The *type* and *key* identify the entity;
    *attributes* (provided as a dict and/or keyword arguments) carry the
    data that JSON Logic rules target.

    Examples::

        Context("user", "user-123", plan="enterprise")
        Context("account", "acme-corp", {"region": "us"}, employee_count=500)
    """

    def __init__(
        self,
        type: str,
        key: str,
        attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self.type = type
        self.key = key
        self.attributes = {**(attributes or {}), **kwargs}

    def __repr__(self) -> str:
        return f"Context(type={self.type!r}, key={self.key!r}, attributes={self.attributes!r})"


class Rule:
    """Fluent builder for JSON Logic rule dicts.

    Usage::

        Rule("Enable for enterprise users")
            .when("user.plan", "==", "enterprise")
            .serve(True)
            .build()

    Multiple ``.when()`` calls are AND'd.  ``.environment()`` tags the
    built dict with an environment key for use with ``Flag.addRule()``.
    """

    def __init__(self, description: str) -> None:
        self._description = description
        self._conditions: list[dict[str, Any]] = []
        self._value: Any = None
        self._environment: str | None = None

    def environment(self, env_key: str) -> Rule:
        """Tag this rule with an environment key (used by ``addRule``)."""
        self._environment = env_key
        return self

    def when(self, var: str, op: str, value: Any) -> Rule:
        """Add a condition.  Multiple calls are AND'd."""
        if op == "contains":
            # JSON Logic "in" with reversed operands: value in var
            self._conditions.append({"in": [value, {"var": var}]})
        else:
            self._conditions.append({op: [{"var": var}, value]})
        return self

    def serve(self, value: Any) -> Rule:
        """Set the value returned when this rule matches."""
        self._value = value
        return self

    def build(self) -> dict[str, Any]:
        """Finalize and return the rule as a plain dict."""
        if len(self._conditions) == 1:
            logic = self._conditions[0]
        elif len(self._conditions) > 1:
            logic = {"and": self._conditions}
        else:
            logic = {}

        result: dict[str, Any] = {
            "description": self._description,
            "logic": logic,
            "value": self._value,
        }

        if self._environment is not None:
            result["environment"] = self._environment

        return result
