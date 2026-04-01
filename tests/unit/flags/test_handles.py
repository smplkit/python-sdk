"""Tests for typed flag handles and context registration buffer."""

from unittest.mock import MagicMock

from smplkit.flags.client import (
    BoolFlagHandle,
    JsonFlagHandle,
    NumberFlagHandle,
    StringFlagHandle,
    _ContextRegistrationBuffer,
)
from smplkit.flags.types import Context


class TestBoolFlagHandle:
    def test_returns_bool(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = True
        handle = BoolFlagHandle(ns, "test", False)
        assert handle.get() is True
        assert handle.key == "test"
        assert handle.default is False

    def test_returns_default_on_non_bool(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = "not a bool"
        handle = BoolFlagHandle(ns, "test", False)
        assert handle.get() is False

    def test_on_change_decorator(self):
        ns = MagicMock()
        handle = BoolFlagHandle(ns, "test", False)

        @handle.on_change
        def listener(event):
            pass

        assert len(handle._listeners) == 1
        assert handle._listeners[0] is listener


class TestStringFlagHandle:
    def test_returns_string(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = "blue"
        handle = StringFlagHandle(ns, "color", "red")
        assert handle.get() == "blue"

    def test_returns_default_on_non_string(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = 42
        handle = StringFlagHandle(ns, "color", "red")
        assert handle.get() == "red"


class TestNumberFlagHandle:
    def test_returns_int(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = 5
        handle = NumberFlagHandle(ns, "retries", 3)
        assert handle.get() == 5

    def test_returns_float(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = 3.14
        handle = NumberFlagHandle(ns, "rate", 1.0)
        assert handle.get() == 3.14

    def test_returns_default_on_bool(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = True  # bool is subclass of int
        handle = NumberFlagHandle(ns, "retries", 3)
        assert handle.get() == 3

    def test_returns_default_on_string(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = "not a number"
        handle = NumberFlagHandle(ns, "retries", 3)
        assert handle.get() == 3


class TestJsonFlagHandle:
    def test_returns_dict(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = {"mode": "dark"}
        handle = JsonFlagHandle(ns, "theme", {"mode": "light"})
        assert handle.get() == {"mode": "dark"}

    def test_returns_default_on_non_dict(self):
        ns = MagicMock()
        ns._evaluate_handle.return_value = "not a dict"
        handle = JsonFlagHandle(ns, "theme", {"mode": "light"})
        assert handle.get() == {"mode": "light"}


class TestContextRegistrationBuffer:
    def test_observe_and_drain(self):
        buf = _ContextRegistrationBuffer()
        buf.observe(
            [
                Context("user", "u-1", plan="enterprise"),
                Context("account", "a-1", region="us"),
            ]
        )
        batch = buf.drain()
        assert len(batch) == 2
        assert batch[0]["id"] == "user:u-1"
        assert batch[0]["name"] == "u-1"
        assert batch[0]["attributes"]["plan"] == "enterprise"

    def test_deduplication(self):
        buf = _ContextRegistrationBuffer()
        buf.observe([Context("user", "u-1", plan="enterprise")])
        buf.observe([Context("user", "u-1", plan="enterprise")])
        batch = buf.drain()
        assert len(batch) == 1

    def test_drain_clears_pending(self):
        buf = _ContextRegistrationBuffer()
        buf.observe([Context("user", "u-1")])
        buf.drain()
        batch = buf.drain()
        assert len(batch) == 0

    def test_pending_count(self):
        buf = _ContextRegistrationBuffer()
        assert buf.pending_count == 0
        buf.observe([Context("user", "u-1"), Context("account", "a-1")])
        assert buf.pending_count == 2
        buf.drain()
        assert buf.pending_count == 0
