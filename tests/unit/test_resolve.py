"""Tests for API key resolution chain."""

from __future__ import annotations

import importlib
import sys
from unittest import mock

import pytest

from smplkit import AsyncSmplClient, SmplClient, SmplError
from smplkit._resolve import _resolve_api_key


class TestResolveApiKey:
    """Unit tests for the _resolve_api_key helper."""

    def test_explicit_key_returned(self):
        assert _resolve_api_key("sk_api_explicit") == "sk_api_explicit"

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_api_env")
        assert _resolve_api_key(None) == "sk_api_env"

    def test_config_file_used_when_no_explicit_no_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        config_file = tmp_path / ".smplkit"
        config_file.write_text('[default]\napi_key = "sk_api_file"\n')
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        assert _resolve_api_key(None) == "sk_api_file"

    def test_none_when_no_key_anywhere(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        assert _resolve_api_key(None) is None

    def test_none_when_file_has_no_api_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        config_file = tmp_path / ".smplkit"
        config_file.write_text("[default]\nother_key = \"value\"\n")
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        assert _resolve_api_key(None) is None

    def test_none_when_file_is_malformed(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        config_file = tmp_path / ".smplkit"
        config_file.write_text("this is not valid toml {{{}}")
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        assert _resolve_api_key(None) is None

    def test_explicit_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_api_env")
        assert _resolve_api_key("sk_api_explicit") == "sk_api_explicit"

    def test_env_takes_precedence_over_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_api_env")
        config_file = tmp_path / ".smplkit"
        config_file.write_text('[default]\napi_key = "sk_api_file"\n')
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        assert _resolve_api_key(None) == "sk_api_env"

    def test_empty_env_var_treated_as_unset(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SMPLKIT_API_KEY", "")
        config_file = tmp_path / ".smplkit"
        config_file.write_text('[default]\napi_key = "sk_api_file"\n')
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        assert _resolve_api_key(None) == "sk_api_file"

    def test_tomli_fallback_when_tomllib_missing(self, monkeypatch, tmp_path):
        """Simulate Python < 3.11 where tomllib is absent."""
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        config_file = tmp_path / ".smplkit"
        config_file.write_text('[default]\napi_key = "sk_api_tomli"\n')
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)

        import tomllib as real_tomllib

        with mock.patch.dict(sys.modules, {"tomllib": None, "tomli": real_tomllib}):
            importlib.reload(sys.modules["smplkit._resolve"])
            from smplkit._resolve import _resolve_api_key as patched_resolve

            assert patched_resolve(None) == "sk_api_tomli"

        # Restore the module
        importlib.reload(sys.modules["smplkit._resolve"])


class TestSmplClientResolution:
    """Integration tests: SmplClient constructor uses resolution chain."""

    def test_explicit_key(self):
        client = SmplClient(api_key="sk_api_test")
        assert client._api_key == "sk_api_test"

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_api_env")
        client = SmplClient()
        assert client._api_key == "sk_api_env"

    def test_config_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        config_file = tmp_path / ".smplkit"
        config_file.write_text('[default]\napi_key = "sk_api_file"\n')
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        client = SmplClient()
        assert client._api_key == "sk_api_file"

    def test_error_when_no_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        with pytest.raises(SmplError, match="No API key provided"):
            SmplClient()

    def test_error_message_lists_all_methods(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        with pytest.raises(SmplError, match="Pass api_key to the constructor"):
            SmplClient()
        with pytest.raises(SmplError, match="SMPLKIT_API_KEY"):
            SmplClient()
        with pytest.raises(SmplError, match=r"~/.smplkit"):
            SmplClient()


class TestAsyncSmplClientResolution:
    """Integration tests: AsyncSmplClient constructor uses resolution chain."""

    def test_explicit_key(self):
        client = AsyncSmplClient(api_key="sk_api_test")
        assert client._api_key == "sk_api_test"

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv("SMPLKIT_API_KEY", "sk_api_env")
        client = AsyncSmplClient()
        assert client._api_key == "sk_api_env"

    def test_error_when_no_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SMPLKIT_API_KEY", raising=False)
        monkeypatch.setattr("smplkit._resolve.Path.home", lambda: tmp_path)
        with pytest.raises(SmplError, match="No API key provided"):
            AsyncSmplClient()
