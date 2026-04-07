# smplkit SDK Examples

Runnable examples demonstrating the [smplkit Python SDK](https://github.com/smplkit/python-sdk).

> **Note:** These examples require valid smplkit credentials and a live environment — they are not self-contained demos.

## Prerequisites

1. Install the SDK:

   ```bash
   pip install smplkit-sdk
   ```

2. A valid smplkit API key, provided via one of:
   - `SMPLKIT_API_KEY` environment variable
   - `~/.smplkit` configuration file (see SDK docs)
3. At least two environments configured (e.g., `staging`, `production`).

## Structure

Each product has two showcases — **management** and **runtime** — plus a setup helper that creates server-side state for the runtime showcase.

| Product | Management | Runtime | Setup |
|---------|-----------|---------|-------|
| **Flags** | `flags_management_showcase.py` | `flags_runtime_showcase.py` | `flags_runtime_setup.py` |
| **Config** | `config_management_showcase.py` | `config_runtime_showcase.py` | `config_runtime_setup.py` |
| **Logging** | `logging_management_showcase.py` | `logging_runtime_showcase.py` | `logging_runtime_setup.py` |

**Management showcases** demonstrate the programmatic CRUD API: creating resources with `new*()` + `save()`, fetching with `get(key)`, listing, mutating, and deleting. No `connect()` or `start()` needed — management methods are stateless HTTP calls.

**Runtime showcases** demonstrate the developer experience: lazy initialization (Flags/Config) or explicit `start()` (Logging), local evaluation, live updates via WebSocket, and change listeners. Each runtime showcase imports its setup helper to create server-side state, then cleans up after itself.

## Running

```bash
# Management (standalone — no setup file needed)
python examples/flags_management_showcase.py
python examples/config_management_showcase.py
python examples/logging_management_showcase.py

# Runtime (imports its setup helper automatically)
python examples/flags_runtime_showcase.py
python examples/config_runtime_showcase.py
python examples/logging_runtime_showcase.py
```

Each script creates temporary resources, exercises all SDK features, then cleans up after itself.
