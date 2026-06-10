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

There is **one** client per product, reached from `SmplClient` (and
`AsyncSmplClient`): `client.config`, `client.flags`, `client.logging`,
`client.audit`, and `client.jobs`. Management/CRUD lives directly on each
product client — `client.config.new/get/list/delete`, the `client.flags.new_*`
builders, and `client.logging.loggers` / `client.logging.log_groups`. Each
product can also be used via a standalone client (`AuditClient`, `JobsClient`).

Config/Flags/Logging keep a **management** + **runtime** showcase pair (the two
sides — CRUD vs. evaluation — are genuinely different). Audit and Jobs have **one**
showcase each — they have no runtime/management split (one client, full surface).

| Product | Management | Runtime | Setup |
|---------|-----------|---------|-------|
| **Flags** | `flags_management_showcase.py` | `flags_runtime_showcase.py` | `flags_runtime_setup.py` |
| **Config** | `config_management_showcase.py` | `config_runtime_showcase.py` | `config_runtime_setup.py` |
| **Logging** | `logging_management_showcase.py` | `logging_runtime_showcase.py` | `logging_runtime_setup.py` |
| **Audit** | `audit_showcase.py` — single; events, discovery, categories, and forwarders | | _(none)_ |
| **Jobs** | `jobs_showcase.py` — single; job CRUD, runs, usage | | _(none)_ |

**Management showcases** demonstrate the programmatic CRUD API directly on the
product client: creating resources with `new*()` + `save()`, fetching with
`get(id)`, listing, mutating, and deleting. No `install()` needed — management
methods are stateless HTTP calls.

**Runtime showcases** demonstrate the developer experience: a per-product
`install()` (`client.config.install()` / `client.flags.install()` /
`client.logging.install()`), local evaluation, live updates via WebSocket, and
change listeners. Each runtime showcase imports its setup helper to create
server-side state, then cleans up after itself.

## Running

```bash
# Single-client products (Audit, Jobs — full surface, no runtime/management split)
python examples/audit_showcase.py
python examples/jobs_showcase.py

# Management / CRUD (directly on client.config / client.flags / client.logging)
python examples/flags_management_showcase.py
python examples/config_management_showcase.py
python examples/logging_management_showcase.py

# Runtime (imports its setup helper automatically)
python examples/flags_runtime_showcase.py
python examples/config_runtime_showcase.py
python examples/logging_runtime_showcase.py
```

Each script creates temporary resources, exercises all SDK features, then cleans up after itself.
