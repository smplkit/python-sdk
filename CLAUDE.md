# smplkit Python SDK

See `~/.claude/CLAUDE.md` for universal rules (git workflow, testing, code quality, SDK conventions, etc.).

## Repository Structure

Two-layer architecture per ADR-021:
- `src/smplkit/_generated/` — Auto-generated client code from OpenAPI specs. Do not edit manually.
- `src/smplkit/` (excluding `_generated/`) — Hand-crafted SDK wrapper. This is the public API.

## Regenerating Clients

```bash
make generate
```

Spec updates are automated: each source repo (app, config, flags, logging) pushes spec changes to this repo via PR. PRs from `regen/` branches authored by `notmikegorman` are auto-merged after CI passes (see `.github/workflows/auto-merge.yml`).

## Testing

```bash
pytest --cov=smplkit --cov-report=term-missing
```

## Python Version Policy

The SDK supports Python 3.10 through 3.13. Development uses Python 3.13 (the latest stable).

- `requires-python = ">=3.10"` in pyproject.toml is the enforced minimum.
- CI runs the full test suite against 3.10, 3.11, 3.12, and 3.13 on every push.
- Do NOT use Python features introduced after 3.10 unless guarded by a version check or `typing_extensions` backport. Specifically avoid:
  - `ExceptionGroup` / `except*` (3.11+)
  - `type` statement for type aliases (3.12+)
  - `typing.override` without `typing_extensions` fallback (3.12+)
  - `itertools.batched` (3.12+)
  - `pathlib.Path.walk` (3.12+)
- PEP 604 union syntax (`X | Y`) IS safe — available from 3.10.
- `from __future__ import annotations` IS safe for forward references.
- When adding new dependencies, verify their minimum Python version is <= 3.10.

## Package Naming

- **PyPI project name:** `smplkit-sdk` (install via `pip install smplkit-sdk`)
- **Python package name:** `smplkit` (import via `from smplkit import SmplkitClient`)
- The PyPI name `smplkit` is taken by an unrelated project.

## Publishing

- Version is derived from git tags via `hatch-vcs`. Do not set version in pyproject.toml.
- Publishes to PyPI via OIDC trusted publishing.

## Wrapper-layer Conventions

These apply to every handwritten dataclass and management surface under
`src/smplkit/` (excluding `_generated/`).

### Dataclass docstrings — Google-style `Attributes:` section

Document each field with a Google-style `Attributes:` section in the
class docstring. PyCharm renders this with field names as clean code
chips and descriptions inline. The `(Type)` annotation parses cleanly
(Sphinx + IDEs both accept it) even though PyCharm's class-hover
strips it from the rendered popup — the type info still lives in the
field annotation immediately below, which PyCharm surfaces on
field-level hover and in autocomplete. Verified empirically: this is
the cleanest of the available formats (PEP-257 attribute docstrings,
Sphinx `:ivar:` with or without inline types, NumPy-style `Attributes
----------`, and Google all tested in PyCharm — Google won on
readability of the names; types are unavailable in class-hover for
any format).

```python
@dataclass(frozen=True, slots=True)
class HttpConfiguration:
    """Forwarder destination HTTP request shape.

    Attributes:
        method (HttpMethod): HTTP verb used for delivery. Defaults to
            ``HttpMethod.POST``.
        url (str): Destination URL the audit service POSTs each event to.
        headers (list[HttpHeader]): Headers attached to every outbound
            request. Values carry credentials and are encrypted at rest
            server-side; reads return them redacted.
        success_status (str): Status the destination must return for
            delivery to count as success — exact code (``"200"``) or
            class (``"2xx"``). Defaults to ``"2xx"``.
    """

    method: HttpMethod = HttpMethod.POST
    url: str = ""
    headers: list[HttpHeader] = field(default_factory=list)
    success_status: str = "2xx"
```

Field declarations stay clean (type + default only — no PEP-257
per-attribute docstrings, no comments). Active-record models (mutable
with `save()`/`delete()`) follow the same convention; their `_client`
field is not a customer-facing attribute and is omitted from the
docstring.

### Never accept `WrapperType | dict[str, Any]` on a public method

The wrapper layer exists to be typed. A `Foo | dict[str, Any]`
signature undermines autocomplete, mypy, and IDE refactoring, and lets
a typo silently ship to the server. Require the typed model. Free-form
JSON payloads (JSON Logic filters, audit event `data`, env-keyed maps)
are legitimately `dict[str, Any]` — that's not a bypass, it's the
actual shape.

### Active-record verbs — `.new()` not `.create()`

Every management resource uses `mgmt.X.new(...)` to construct an
unsaved instance, then `instance.save()` to persist. The model's
`save()` upserts based on whether `created_at` is set. `instance.delete()`
removes. No public `create(...)` or `update(...)` verbs on the client
— `_create()` and `_update()` are internals invoked by `save()`. The
client may keep a parallel `delete(id)` for callers who never fetched
the resource (parity with `EnvironmentsClient.delete`).
