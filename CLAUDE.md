# smplkit Python SDK

## Repository structure

Two-layer architecture per ADR-021:
- `src/smplkit/_generated/` — Auto-generated client code from OpenAPI specs. Do not edit manually.
- `src/smplkit/` (excluding `_generated/`) — Hand-crafted SDK wrapper. This is the public API.

## Regenerating clients

After updating a spec in `openapi/`:
```bash
bash scripts/generate.sh
```

Do NOT edit files under `_generated/` manually — they will be overwritten on next generation.

## Commits

Commit directly to main with conventional commit messages. No branches or PRs.
Exception: automated regeneration PRs from `regenerate-clients.yml` use branches by design.

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

## Publishing

- Publishing is triggered by git tags: `git tag v0.1.0 && git push --tags`
- Uses PyPI trusted publishing (OIDC) — no API tokens
- Do not publish without explicit instruction from the developer
