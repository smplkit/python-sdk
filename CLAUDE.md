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
Exception: automated spec-update PRs from `receive-spec-update.yml` use branches by design.

## Testing

```bash
pytest --cov=smplkit --cov-report=term-missing
```

Target 90%+ coverage on the SDK wrapper layer. Generated code coverage is not enforced.

## Publishing

- Publishing is triggered by git tags: `git tag v0.1.0 && git push --tags`
- Uses PyPI trusted publishing (OIDC) — no API tokens
- Do not publish without explicit instruction from the developer
