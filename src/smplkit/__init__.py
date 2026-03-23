"""smplkit — Official Python SDK for the smplkit platform."""

from smplkit.client import SmplkitClient

__all__ = ["SmplkitClient"]

try:
    from smplkit._version import __version__
except ImportError:
    __version__ = "0.0.0"  # Fallback for editable installs without VCS
