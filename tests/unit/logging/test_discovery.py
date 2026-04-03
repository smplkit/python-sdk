"""Tests for auto-discovery of Python loggers."""

import logging as stdlib_logging

from smplkit.logging._discovery import (
    discover_existing_loggers,
    install_discovery_patch,
    uninstall_discovery_patch,
)


class TestDiscoverExistingLoggers:
    def test_finds_root(self):
        loggers = discover_existing_loggers()
        names = [name for name, _ in loggers]
        assert "root" in names

    def test_finds_pre_existing_logger(self):
        # Create a logger before discovery
        test_name = "test.discover.pre_existing_abc123"
        stdlib_logging.getLogger(test_name)
        loggers = discover_existing_loggers()
        names = [name for name, _ in loggers]
        assert test_name in names

    def test_returns_effective_level(self):
        test_name = "test.discover.level_check_xyz"
        lg = stdlib_logging.getLogger(test_name)
        lg.setLevel(stdlib_logging.ERROR)
        loggers = discover_existing_loggers()
        level_map = dict(loggers)
        assert level_map[test_name] == stdlib_logging.ERROR

    def test_skips_placeholder_objects(self):
        # PlaceHolders are created for intermediate names
        # e.g., getLogger("a.b.c") creates PlaceHolder for "a" and "a.b"
        # Verify we only get Logger instances
        test_name = "test.placeholder.skip.deep.logger"
        stdlib_logging.getLogger(test_name)
        loggers = discover_existing_loggers()
        for name, _ in loggers:
            obj = stdlib_logging.root.manager.loggerDict.get(name)
            if obj is not None:
                assert isinstance(obj, stdlib_logging.Logger)


class TestDiscoveryPatch:
    def setup_method(self):
        # Ensure patch is uninstalled before each test
        uninstall_discovery_patch()

    def teardown_method(self):
        uninstall_discovery_patch()

    def test_detects_new_logger(self):
        discovered = []

        def on_new(name, level):
            discovered.append((name, level))

        install_discovery_patch(on_new)
        test_name = "test.patch.new_logger_detect_001"
        stdlib_logging.getLogger(test_name)
        assert any(name == test_name for name, _ in discovered)

    def test_does_not_fire_for_existing_logger(self):
        test_name = "test.patch.existing_no_fire_002"
        stdlib_logging.getLogger(test_name)  # Create before patch

        discovered = []

        def on_new(name, level):
            discovered.append((name, level))

        install_discovery_patch(on_new)
        stdlib_logging.getLogger(test_name)  # Get again — not new
        assert not any(name == test_name for name, _ in discovered)

    def test_uninstall_restores_original(self):
        discovered = []

        def on_new(name, level):
            discovered.append((name, level))

        install_discovery_patch(on_new)
        uninstall_discovery_patch()

        test_name = "test.patch.after_uninstall_003"
        stdlib_logging.getLogger(test_name)
        assert not any(name == test_name for name, _ in discovered)

    def test_double_install_is_noop(self):
        calls_1 = []
        calls_2 = []

        install_discovery_patch(lambda n, l: calls_1.append(n))
        install_discovery_patch(lambda n, l: calls_2.append(n))

        test_name = "test.patch.double_install_004"
        stdlib_logging.getLogger(test_name)
        # First callback should be active
        assert test_name in calls_1
        # Second was ignored
        assert test_name not in calls_2
