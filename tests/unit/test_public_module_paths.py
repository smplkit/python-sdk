"""Guard against private-module leaks on the public SDK surface.

Every symbol re-exported from ``smplkit`` (or one of its public subpackages)
carries a ``__module__`` that IDEs, ``help()``, ``repr()``, and Sphinx render
as the symbol's canonical home. If that value points at a private (underscore-
prefixed) module — e.g. ``smplkit.audit._client`` instead of ``smplkit.audit``
— customers see internal plumbing on hover, which is a documentation leak.

These tests encode the exact check that found the original leak: walk each
public ``__all__`` and assert no export advertises a private module segment.
A second test walks the sub-namespace clients reachable as attributes on a
constructed client (e.g. ``client.platform.environments``), which are not
listed in any ``__all__`` but are equally customer-visible.

Pure import + introspection — no network and no credentials required; an
explicit ``api_key`` is passed where a client is constructed, so nothing
resolves ``~/.smplkit``.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect

import pytest

# Every public package whose ``__all__`` defines customer-facing surface.
_PUBLIC_PACKAGES = [
    "smplkit",
    "smplkit.account",
    "smplkit.audit",
    "smplkit.config",
    "smplkit.flags",
    "smplkit.jobs",
    "smplkit.logging",
    "smplkit.platform",
]


def _private_segment(module_name: str | None) -> str | None:
    """Return the first underscore-prefixed segment of ``module_name``, if any.

    ``"smplkit.audit._client"`` -> ``"_client"``; ``"smplkit.audit"`` -> None.
    Dunder modules (``__main__``) are not what we guard against here, but a
    leading-underscore segment of any kind is a private path, so we flag it.
    """
    if not module_name:
        return None
    for segment in module_name.split("."):
        if segment.startswith("_"):
            return segment
    return None


def _all_exports() -> list[tuple[str, str]]:
    """Yield ``(package, export_name)`` for every name in each public __all__."""
    params: list[tuple[str, str]] = []
    for pkg_name in _PUBLIC_PACKAGES:
        pkg = importlib.import_module(pkg_name)
        for name in pkg.__all__:
            params.append((pkg_name, name))
    return params


@pytest.mark.parametrize(
    ("package_name", "export_name"),
    _all_exports(),
    ids=lambda v: v,
)
def test_public_export_has_no_private_module(package_name: str, export_name: str) -> None:
    """No symbol in a public ``__all__`` may advertise a private module path."""
    pkg = importlib.import_module(package_name)
    obj = getattr(pkg, export_name)
    module_name = getattr(obj, "__module__", None)
    leaked = _private_segment(module_name)
    assert leaked is None, (
        f"{package_name}.{export_name} leaks a private module: "
        f"__module__ == {module_name!r} (segment {leaked!r}). "
        f"Set {export_name}.__module__ to its canonical public package."
    )


# (top-level namespace, nested sub-namespace accessors). These sub-namespace
# clients (``EnvironmentsClient``, ``SettingsClient``, ``EventsClient``, …) are
# not in any package ``__all__`` but are customer-visible on the client object
# graph, so their ``__module__`` must be clean too.
_SUBNAMESPACE_ACCESSORS = {
    "audit": ("events", "resource_types", "event_types", "categories", "forwarders"),
    "config": (),
    "flags": (),
    "logging": ("loggers", "log_groups"),
    "jobs": ("runs",),
    "platform": ("environments", "services", "contexts", "context_types"),
    "account": ("settings",),
}


@pytest.mark.parametrize("client_kind", ["sync", "async"])
def test_reachable_subnamespace_clients_have_no_private_module(client_kind: str) -> None:
    """Attribute-reachable sub-namespace clients must not leak a private path.

    Built inside the test body (not at parametrize/collection time) so the
    autouse fixtures that no-op telemetry and set ``SMPLKIT_SERVICE`` apply.
    """
    from smplkit import AsyncSmplClient, SmplClient

    client_cls = SmplClient if client_kind == "sync" else AsyncSmplClient
    client = client_cls(api_key="sk_test", base_domain="example.test")

    leaks: list[str] = []
    try:
        for ns_name, sub_names in _SUBNAMESPACE_ACCESSORS.items():
            namespaces = [getattr(client, ns_name)]
            namespaces.extend(getattr(namespaces[0], sub) for sub in sub_names)
            for obj in namespaces:
                module_name = type(obj).__module__
                if _private_segment(module_name) is not None:
                    leaks.append(f"{type(obj).__name__} -> {module_name}")
    finally:
        # SmplClient.close() is sync; AsyncSmplClient.close() is a coroutine.
        result = client.close()
        if inspect.isawaitable(result):
            asyncio.run(result)

    assert not leaks, f"{client_kind} sub-namespace clients leak private modules: {leaks}"
