"""API key resolution chain: explicit → env var → config file."""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_api_key(explicit: str | None) -> str | None:
    """Resolve API key from explicit value, env var, or config file."""
    if explicit:
        return explicit

    env_val = os.environ.get("SMPLKIT_API_KEY")
    if env_val:
        return env_val

    config_path = Path.home() / ".smplkit"
    if config_path.is_file():
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]  # Python < 3.11 fallback
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
            api_key = config.get("default", {}).get("api_key")
            if api_key:
                return api_key
        except Exception:
            pass  # Malformed file — skip silently

    return None
