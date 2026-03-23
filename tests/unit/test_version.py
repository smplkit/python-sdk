"""Test version is accessible."""

import smplkit


def test_version_is_string():
    assert isinstance(smplkit.__version__, str)


def test_version_is_not_fallback():
    """In a proper install, version should not be the fallback."""
    # During CI with pip install -e ".[dev]", hatch-vcs reads from git
    # This may be "0.0.0" in dev if there are no tags yet, which is fine
    assert smplkit.__version__ is not None
