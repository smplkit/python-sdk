"""Public types for the Flags SDK: Context, FlagDeclaration, Op, Rule."""

from __future__ import annotations

import dataclasses
import enum
from typing import Any


class Op(str, enum.Enum):
    """Operators supported by :meth:`Rule.when`.

    Customers should prefer ``Op.EQ`` etc. over raw strings so the IDE
    can validate calls.  Raw strings are still accepted for backward
    compatibility.
    """

    EQ = "=="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    IN = "in"
    CONTAINS = "contains"


class Context:
    """A typed evaluation context entity.

    Represents a single entity (user, account, device, etc.) in the
    evaluation context.  The *type* and *key* identify the entity;
    *attributes* (provided as a dict and/or keyword arguments) carry the
    data that targeting rules evaluate against.

    Examples::

        Context("user", "user-123", plan="enterprise")
        Context("account", "acme-corp", {"region": "us"}, employee_count=500)
    """

    type: str
    key: str
    name: str | None
    attributes: dict[str, Any]

    def __init__(
        self,
        type: str,
        key: str,
        attributes: dict[str, Any] | None = None,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.type = type
        self.key = key
        self.name = name
        self.attributes = {**(attributes or {}), **kwargs}

    def __repr__(self) -> str:
        return f"Context(type={self.type!r}, key={self.key!r}, name={self.name!r}, attributes={self.attributes!r})"


@dataclasses.dataclass
class FlagDeclaration:
    """Describes a flag declaration for buffered registration.

    Used by :meth:`smplkit.SmplManagementClient.flags.register` to queue
    declarations for bulk registration.  ``service`` and ``environment``
    default to ``None``; the runtime client fills them from the active
    ``SmplClient`` when it forwards declarations.
    """

    id: str
    type: str
    default: Any
    service: str | None = None
    environment: str | None = None


class Rule:
    """Fluent builder for flag targeting rules.

    Usage::

        Rule("Enable for enterprise users")
            .when("user.plan", Op.EQ, "enterprise")
            .serve(True)
            .build()

    Multiple ``.when()`` calls are AND'd.  Use ``.environment()`` to
    scope the rule to a specific environment for ``Flag.addRule()``.
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

    def when(self, var: str, op: Op | str, value: Any) -> Rule:
        """Add a condition.  Multiple calls are AND'd.

        ``op`` accepts an :class:`Op` enum value (preferred) or a raw
        string (e.g. ``"=="``, ``"contains"``).
        """
        op_str = op.value if isinstance(op, Op) else op
        if op_str == "contains":
            # JSON Logic "in" with reversed operands: value in var
            self._conditions.append({"in": [value, {"var": var}]})
        else:
            self._conditions.append({op_str: [{"var": var}, value]})
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
