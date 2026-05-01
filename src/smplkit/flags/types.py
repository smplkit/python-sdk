"""Public types for the Flags SDK: Context, FlagDeclaration, Op, Rule."""

from __future__ import annotations

import dataclasses
import enum
from typing import Any, overload


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

        Rule("Enable for enterprise users", environment="staging")
            .when("user.plan", Op.EQ, "enterprise")
            .serve(True)

    Multiple ``.when()`` calls are AND'd.  ``environment`` is required so the
    target environment is unambiguous when the rule is passed to
    :meth:`Flag.add_rule`.  ``.serve()`` finalizes the rule and returns the
    built dict ready to pass to ``add_rule``.
    """

    def __init__(self, description: str, *, environment: str) -> None:
        self._description = description
        self._conditions: list[dict[str, Any]] = []
        self._environment = environment

    @overload
    def when(self, expr: dict[str, Any], /) -> Rule: ...
    @overload
    def when(self, var: str, op: Op | str, value: Any, /) -> Rule: ...

    def when(self, *args: Any) -> Rule:
        """Add a condition.  Multiple calls are AND'd at the top level.

        Two forms:

        - ``when(var, op, value)`` — convenience for simple comparisons.
          ``op`` accepts an :class:`Op` enum value (preferred) or a raw
          string (e.g. ``"=="``, ``"contains"``).

        - ``when(expr)`` — escape hatch accepting an arbitrary JSON Logic
          expression (use this for OR, nested AND/OR, ``if``, etc.).
          See https://jsonlogic.com/ for the full expression grammar.
        """
        if len(args) == 1 and isinstance(args[0], dict):
            self._conditions.append(args[0])
            return self
        if len(args) == 3:
            var, op, value = args
            op_str = op.value if isinstance(op, Op) else op
            if op_str == "contains":
                # JSON Logic "in" with reversed operands: value in var
                self._conditions.append({"in": [value, {"var": var}]})
            else:
                self._conditions.append({op_str: [{"var": var}, value]})
            return self
        raise TypeError(f"Rule.when() takes either (var, op, value) or a single JSON Logic dict; got args={args!r}")

    def serve(self, value: Any) -> dict[str, Any]:
        """Finalize the rule with *value* served on match and return the built dict."""
        if len(self._conditions) == 1:
            logic = self._conditions[0]
        elif len(self._conditions) > 1:
            logic = {"and": self._conditions}
        else:
            logic = {}

        return {
            "description": self._description,
            "logic": logic,
            "value": value,
            "environment": self._environment,
        }
