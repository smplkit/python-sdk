"""Shared fixtures for all tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _set_smplkit_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure SMPLKIT_SERVICE is set for every test.

    ``service`` is now required by SmplClient / AsyncSmplClient.  This
    autouse fixture keeps existing tests green without individual changes.
    Tests that need to exercise the service-missing error path should
    explicitly ``monkeypatch.delenv("SMPLKIT_SERVICE", raising=False)``.
    """
    monkeypatch.setenv("SMPLKIT_SERVICE", "test-service")
