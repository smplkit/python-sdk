"""Tests for StdlibLoggingAdapter."""

from __future__ import annotations

import logging as stdlib_logging

from smplkit.logging.adapters.stdlib_logging import StdlibLoggingAdapter


class TestDiscover:
    def test_finds_existing_loggers(self):
        test_name = "test.stdlib_adapter.discover_existing_001"
        stdlib_logging.getLogger(test_name)
        adapter = StdlibLoggingAdapter()
        result = adapter.discover()
        names = [n for n, _ in result]
        assert test_name in names

    def test_finds_root(self):
        adapter = StdlibLoggingAdapter()
        result = adapter.discover()
        names = [n for n, _ in result]
        assert "root" in names

    def test_skips_placeholders(self):
        test_name = "test.stdlib_adapter.placeholder.deep.logger_002"
        stdlib_logging.getLogger(test_name)
        adapter = StdlibLoggingAdapter()
        result = adapter.discover()
        for name, _ in result:
            obj = stdlib_logging.root.manager.loggerDict.get(name)
            if obj is not None:
                assert isinstance(obj, stdlib_logging.Logger)

    def test_with_prefix_filter(self):
        test_name = "test.stdlib_adapter.prefix.match_003"
        other_name = "other.stdlib_adapter.prefix.no_match_003"
        stdlib_logging.getLogger(test_name)
        stdlib_logging.getLogger(other_name)
        adapter = StdlibLoggingAdapter(prefix="test.stdlib_adapter.prefix")
        result = adapter.discover()
        names = [n for n, _ in result]
        assert test_name in names
        assert other_name not in names
        # root should not be included when prefix is set
        assert "root" not in names

    def test_discover_existing_false(self):
        test_name = "test.stdlib_adapter.no_discover_004"
        stdlib_logging.getLogger(test_name)
        adapter = StdlibLoggingAdapter(discover_existing=False)
        result = adapter.discover()
        assert result == []

    def test_returns_effective_level(self):
        test_name = "test.stdlib_adapter.level_check_005"
        lg = stdlib_logging.getLogger(test_name)
        lg.setLevel(stdlib_logging.ERROR)
        adapter = StdlibLoggingAdapter()
        result = adapter.discover()
        level_map = dict(result)
        assert level_map[test_name] == stdlib_logging.ERROR


class TestApplyLevel:
    def test_sets_level_on_logger(self):
        test_name = "test.stdlib_adapter.apply_level_006"
        lg = stdlib_logging.getLogger(test_name)
        lg.setLevel(stdlib_logging.DEBUG)
        adapter = StdlibLoggingAdapter()
        adapter.apply_level(test_name, stdlib_logging.ERROR)
        assert lg.level == stdlib_logging.ERROR


class TestInstallHook:
    def setup_method(self):
        self.adapter = StdlibLoggingAdapter()

    def teardown_method(self):
        self.adapter.uninstall_hook()

    def test_detects_new_loggers(self):
        discovered = []

        def on_new(name, level):
            discovered.append((name, level))

        self.adapter.install_hook(on_new)
        test_name = "test.stdlib_adapter.hook.new_007"
        stdlib_logging.getLogger(test_name)
        assert any(name == test_name for name, _ in discovered)

    def test_does_not_fire_for_existing(self):
        test_name = "test.stdlib_adapter.hook.existing_008"
        stdlib_logging.getLogger(test_name)

        discovered = []
        self.adapter.install_hook(lambda n, _lv: discovered.append(n))
        stdlib_logging.getLogger(test_name)
        assert test_name not in discovered

    def test_idempotent_install(self):
        calls_1 = []
        calls_2 = []

        self.adapter.install_hook(lambda n, _: calls_1.append(n))
        self.adapter.install_hook(lambda n, _: calls_2.append(n))

        test_name = "test.stdlib_adapter.hook.idempotent_009"
        stdlib_logging.getLogger(test_name)
        assert test_name in calls_1
        assert test_name not in calls_2

    def test_prefix_filter_in_hook(self):
        adapter = StdlibLoggingAdapter(prefix="test.stdlib_adapter.hook.prefix")
        discovered = []
        adapter.install_hook(lambda n, _: discovered.append(n))

        match_name = "test.stdlib_adapter.hook.prefix.match_010"
        no_match = "other.no_match_010"
        stdlib_logging.getLogger(match_name)
        stdlib_logging.getLogger(no_match)

        assert match_name in discovered
        assert no_match not in discovered
        adapter.uninstall_hook()


class TestUninstallHook:
    def test_restores_original(self):
        adapter = StdlibLoggingAdapter()
        discovered = []
        adapter.install_hook(lambda n, _: discovered.append(n))
        adapter.uninstall_hook()

        test_name = "test.stdlib_adapter.uninstall_011"
        stdlib_logging.getLogger(test_name)
        assert test_name not in discovered

    def test_uninstall_without_install_is_noop(self):
        adapter = StdlibLoggingAdapter()
        adapter.uninstall_hook()  # Should not raise
