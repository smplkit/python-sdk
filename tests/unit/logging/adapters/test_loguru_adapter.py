"""Tests for LoguruAdapter."""

from __future__ import annotations

import logging as stdlib_logging

import pytest

loguru = pytest.importorskip("loguru")

from smplkit.logging.adapters.loguru_adapter import LoguruAdapter  # noqa: E402


class TestDiscover:
    def test_returns_empty(self):
        adapter = LoguruAdapter()
        assert adapter.discover() == []


class TestName:
    def test_name(self):
        adapter = LoguruAdapter()
        assert adapter.name == "loguru"


class TestApplyLevel:
    def test_calls_enable(self):
        adapter = LoguruAdapter()
        # enable should not raise
        adapter.apply_level("myapp.module", stdlib_logging.DEBUG)

    def test_calls_disable_for_critical(self):
        adapter = LoguruAdapter()
        # disable should not raise
        adapter.apply_level("myapp.module", stdlib_logging.CRITICAL)


class TestInstallHook:
    def setup_method(self):
        self.adapter = LoguruAdapter()

    def teardown_method(self):
        self.adapter.uninstall_hook()

    def test_detects_bind_with_name(self):
        discovered = []

        def on_new(name, level):
            discovered.append((name, level))

        self.adapter.install_hook(on_new)
        loguru.logger.bind(name="test.loguru.bind_001")
        assert any(n == "test.loguru.bind_001" for n, _ in discovered)

    def test_does_not_fire_for_duplicate(self):
        discovered = []
        self.adapter.install_hook(lambda n, _: discovered.append(n))
        loguru.logger.bind(name="test.loguru.dup_002")
        loguru.logger.bind(name="test.loguru.dup_002")
        assert discovered.count("test.loguru.dup_002") == 1

    def test_ignores_bind_without_name(self):
        discovered = []
        self.adapter.install_hook(lambda n, _: discovered.append(n))
        loguru.logger.bind(foo="bar")
        assert len(discovered) == 0

    def test_idempotent_install(self):
        calls = []
        self.adapter.install_hook(lambda n, _: calls.append(n))
        self.adapter.install_hook(lambda n, _: None)  # should be ignored
        loguru.logger.bind(name="test.loguru.idempotent_003")
        assert "test.loguru.idempotent_003" in calls

    def test_custom_name_field(self):
        adapter = LoguruAdapter(name_field="logger_name")
        discovered = []
        adapter.install_hook(lambda n, _: discovered.append(n))
        loguru.logger.bind(logger_name="test.loguru.custom_004")
        assert "test.loguru.custom_004" in discovered
        adapter.uninstall_hook()


class TestUninstallHook:
    def test_restores_original(self):
        adapter = LoguruAdapter()
        discovered = []
        adapter.install_hook(lambda n, _: discovered.append(n))
        adapter.uninstall_hook()
        loguru.logger.bind(name="test.loguru.after_uninstall_005")
        assert "test.loguru.after_uninstall_005" not in discovered

    def test_uninstall_without_install_is_noop(self):
        adapter = LoguruAdapter()
        adapter.uninstall_hook()  # Should not raise
