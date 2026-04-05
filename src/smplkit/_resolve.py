"""API key resolution chain: explicit → env var → config file."""

from __future__ import annotations

import configparser
import os
from pathlib import Path


def _resolve_api_key(explicit: str | None, environment: str) -> str | None:
    """Resolve API key from explicit value, env var, or config file.

    The config file (``~/.smplkit``) is tried with the *environment*-scoped
    section first (e.g. ``[production]``), then ``[default]``.
    """
    if explicit:
        return explicit

    env_val = os.environ.get("SMPLKIT_API_KEY")
    if env_val:
        return env_val

    config_path = Path.home() / ".smplkit"
    if config_path.is_file():
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            # Try environment-scoped section first
            try:
                return config.get(environment, "api_key")
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass
            # Fall back to [default]
            return config.get("default", "api_key")
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None
        except Exception:
            pass  # Malformed file — skip silently

    return None
