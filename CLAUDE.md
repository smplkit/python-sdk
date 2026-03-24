# smplkit Python SDK

## Repository structure

Two-layer architecture per ADR-021:
- `src/smplkit/_generated/` — Auto-generated client code from OpenAPI specs. Do not edit manually.
- `src/smplkit/` (excluding `_generated/`) — Hand-crafted SDK wrapper. This is the public API.

## Regenerating clients

```bash
make generate
```

This regenerates ALL clients from ALL specs in `openapi/`. Do NOT edit files under `_generated/` manually — they will be overwritten on next generation.

Spec updates are automated: each source repo (app, config, flags, logging) pushes spec changes to this repo via PR. See `docs/source-repo-workflow.yml` for the template. PRs from `regen/` branches authored by `notmikegorman` are auto-merged after CI passes (see `.github/workflows/auto-merge.yml`).

## Commits

Commit directly to main with conventional commit messages. No branches or PRs.
Exception: automated regeneration PRs from source repos use `regen/` branches by design.

## Testing

```bash
pytest --cov=smplkit --cov-report=term-missing
```

Target 90%+ coverage on the SDK wrapper layer. Generated code coverage is not enforced.

## Python Version Policy

The SDK supports Python 3.10 through 3.13. Development uses Python 3.13 (the latest stable).

- `requires-python = ">=3.10"` in pyproject.toml is the enforced minimum.
- CI runs the full test suite against 3.10, 3.11, 3.12, and 3.13 on every push.
- Do NOT use Python features introduced after 3.10 unless they are guarded by a version check or `typing_extensions` backport. Specifically avoid:
  - `ExceptionGroup` / `except*` (3.11+)
  - `type` statement for type aliases (3.12+)
  - `typing.override` without `typing_extensions` fallback (3.12+)
  - `itertools.batched` (3.12+)
  - `pathlib.Path.walk` (3.12+)
- PEP 604 union syntax (`X | Y`) IS safe — it's available from 3.10.
- `from __future__ import annotations` IS safe for forward references if needed.
- When adding new dependencies, verify their minimum Python version is <= 3.10.

## Package Naming

- **PyPI project name:** `smplkit-sdk` (install via `pip install smplkit-sdk`)
- **Python package name:** `smplkit` (import via `from smplkit import SmplkitClient`)
- The PyPI name `smplkit` is taken by an unrelated project. The `-sdk` suffix is the PyPI project name only; it does not affect imports.

## Publishing

Publishing is fully automated in a single workflow (`publish.yml`):

1. Every push to main triggers `publish.yml`, which runs `semantic-release`.
2. If conventional commits warrant a version bump, semantic-release creates a git tag (`vX.Y.Z`) and GitHub release.
3. The same workflow then builds the package and publishes to PyPI via OIDC trusted publishing.

- **Do not create tags manually.** Semantic-release owns versioning.
- **Do not set version in pyproject.toml.** Version is derived from git tags via `hatch-vcs`.
- **Conventional commits drive version bumps:** `feat:` → minor, `fix:` → patch, `BREAKING CHANGE:` → major.
- **PyPI project name:** `smplkit-sdk` (the `smplkit` name on PyPI is taken by an unrelated project).
- **Python package name:** `smplkit` (import path is unchanged: `from smplkit import SmplkitClient`).
