"""Test version is accessible."""

import smplkit


def test_version():
    assert smplkit.__version__ == "0.1.0"
