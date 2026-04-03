"""Tests for the level resolution algorithm."""

from smplkit.logging._resolution import resolve_level


class TestResolveLevelBasic:
    def test_logger_env_level_wins(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": "DEBUG",
                "group": None,
                "managed": True,
                "environments": {"production": {"level": "ERROR"}},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "ERROR"

    def test_logger_base_level_when_no_env(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": "DEBUG",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "DEBUG"

    def test_logger_base_level_when_different_env(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": "DEBUG",
                "group": None,
                "managed": True,
                "environments": {"staging": {"level": "TRACE"}},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "DEBUG"

    def test_fallback_to_info(self):
        assert resolve_level("unknown.logger", "production", {}, {}) == "INFO"


class TestResolveLevelGroupChain:
    def test_group_env_level(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": None,
                "group": "group-1",
                "managed": True,
                "environments": {},
            }
        }
        groups = {
            "group-1": {
                "key": "db-loggers",
                "level": "WARN",
                "group": None,
                "environments": {"production": {"level": "ERROR"}},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, groups) == "ERROR"

    def test_group_base_level(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": None,
                "group": "group-1",
                "managed": True,
                "environments": {},
            }
        }
        groups = {
            "group-1": {
                "key": "db-loggers",
                "level": "WARN",
                "group": None,
                "environments": {},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, groups) == "WARN"

    def test_nested_group_chain(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": None,
                "group": "group-child",
                "managed": True,
                "environments": {},
            }
        }
        groups = {
            "group-child": {
                "key": "child",
                "level": None,
                "group": "group-parent",
                "environments": {},
            },
            "group-parent": {
                "key": "parent",
                "level": "FATAL",
                "group": None,
                "environments": {},
            },
        }
        assert resolve_level("com.example.sql", "production", loggers, groups) == "FATAL"

    def test_group_cycle_does_not_infinite_loop(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": None,
                "group": "group-a",
                "managed": True,
                "environments": {},
            }
        }
        groups = {
            "group-a": {
                "key": "a",
                "level": None,
                "group": "group-b",
                "environments": {},
            },
            "group-b": {
                "key": "b",
                "level": None,
                "group": "group-a",
                "environments": {},
            },
        }
        # Should fall through to INFO without looping
        assert resolve_level("com.example.sql", "production", loggers, groups) == "INFO"


class TestResolveLevelDotAncestry:
    def test_parent_logger_level(self):
        loggers = {
            "com.example": {
                "key": "com.example",
                "level": "WARN",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "WARN"

    def test_grandparent_logger_level(self):
        loggers = {
            "com": {
                "key": "com",
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "ERROR"

    def test_closest_ancestor_wins(self):
        loggers = {
            "com": {
                "key": "com",
                "level": "ERROR",
                "group": None,
                "managed": True,
                "environments": {},
            },
            "com.example": {
                "key": "com.example",
                "level": "DEBUG",
                "group": None,
                "managed": True,
                "environments": {},
            },
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "DEBUG"

    def test_group_takes_precedence_over_dot_ancestor(self):
        loggers = {
            "com.example.sql": {
                "key": "com.example.sql",
                "level": None,
                "group": "group-1",
                "managed": True,
                "environments": {},
            },
            "com.example": {
                "key": "com.example",
                "level": "DEBUG",
                "group": None,
                "managed": True,
                "environments": {},
            },
        }
        groups = {
            "group-1": {
                "key": "sql-group",
                "level": "ERROR",
                "group": None,
                "environments": {},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, groups) == "ERROR"

    def test_ancestor_env_level(self):
        loggers = {
            "com.example": {
                "key": "com.example",
                "level": "DEBUG",
                "group": None,
                "managed": True,
                "environments": {"production": {"level": "FATAL"}},
            }
        }
        assert resolve_level("com.example.sql", "production", loggers, {}) == "FATAL"


class TestResolveLevelEdgeCases:
    def test_logger_not_in_loggers_dict(self):
        assert resolve_level("nonexistent", "prod", {}, {}) == "INFO"

    def test_group_id_not_in_groups_dict(self):
        loggers = {
            "com.example": {
                "key": "com.example",
                "level": None,
                "group": "missing-group-id",
                "managed": True,
                "environments": {},
            }
        }
        # Falls through group chain (missing), then no dot ancestry, fallback
        assert resolve_level("com.example", "prod", loggers, {}) == "INFO"

    def test_empty_environments_dict(self):
        loggers = {
            "test": {
                "key": "test",
                "level": "WARN",
                "group": None,
                "managed": True,
                "environments": None,
            }
        }
        assert resolve_level("test", "prod", loggers, {}) == "WARN"
