# CLAUDE.md — smplkit Python SDK

## Repository purpose
This is the official smplkit Python SDK, published to PyPI as `smplkit`. It provides a curated Python interface to smplkit's APIs.

## Architecture
The SDK uses a two-layer architecture:
- `src/smplkit/_generated/` — Auto-generated client code from OpenAPI specs. Do not edit manually. Do not import from this directory in consumer-facing code.
- `src/smplkit/` (everything outside `_generated/`) — Hand-crafted SDK wrapper providing the public API.

## Client regeneration
Generated client code is produced by `openapi-python-client` from specs in `openapi/`. To regenerate:
1. Ensure the spec in `openapi/{service}.json` is up to date
2. Run `bash scripts/generate.sh`
3. Commit the regenerated `_generated/` directory

Regeneration is also triggered automatically via `repository_dispatch` from service repos when their OpenAPI spec changes.

## Commits
- Commit directly to main (solo phase — no branches or PRs)
- Use conventional commit messages: `feat:`, `fix:`, `chore:`, etc.
- Exception: automated regeneration PRs from the `regenerate.yml` workflow are merged via PR

## Testing
- Run tests: `pytest`
- Minimum 90% code coverage target

## Publishing
- Publishing is triggered by git tags: `git tag v0.1.0 && git push --tags`
- Uses PyPI trusted publishing (OIDC) — no API tokens
- Do not publish without explicit instruction from the developer
