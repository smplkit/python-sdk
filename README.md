# smplkit Python SDK

[![PyPI Version](https://img.shields.io/pypi/v/smplkit-sdk)](https://pypi.org/project/smplkit-sdk/) [![Build](https://github.com/smplkit/python-sdk/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/smplkit/python-sdk/actions) [![Coverage](https://codecov.io/gh/smplkit/python-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/smplkit/python-sdk) [![License](https://img.shields.io/pypi/l/smplkit-sdk)](LICENSE) [![Docs](https://img.shields.io/badge/docs-docs.smplkit.com-blue)](https://docs.smplkit.com)

The official Python SDK for [smplkit](https://www.smplkit.com) — simple application infrastructure that just works.

## Installation

```bash
pip install smplkit-sdk
```

## Requirements

- Python 3.10+

## Quick Start

The SDK ships two top-level clients, each with a clearly-scoped purpose:

| Client | Use case | Construction side effects |
|--------|----------|---------------------------|
| `SmplClient` / `AsyncSmplClient` | **Runtime instrumentation** — flag evaluation, config reads, log emission | Auto-registers a service context, starts a metrics thread, opens a websocket |
| `SmplManagementClient` / `AsyncSmplManagementClient` | **Management / CRUD** — setup scripts, CI/CD, admin tooling | None — pure HTTP setup |

### Runtime: `SmplClient`

```python
from smplkit import SmplClient

with SmplClient(api_key="sk_api_...", environment="production", service="my-svc") as client:
    # Resolve config values for the current environment
    db = client.config.get("database")  # {"host": "...", "port": 5432}

    # Evaluate a flag against the current request context
    checkout_v2 = client.flags.booleanFlag("checkout-v2", default=False)
    if checkout_v2.get():
        ...

    # Opt in to runtime logging level control
    client.logging.start()
```

### Management: `SmplManagementClient`

```python
from smplkit import SmplManagementClient

with SmplManagementClient(api_key="sk_api_...") as mgmt:
    # Configs
    cfg = mgmt.configs.new("my_service", name="My Service")
    cfg.save()
    configs = mgmt.configs.list()

    # Flags
    flag = mgmt.flags.newBooleanFlag("checkout-v2", default=False)
    flag.save()
    flags = mgmt.flags.list()

    # Loggers + log groups
    logger = mgmt.loggers.new("sql", name="SQL Logger")
    logger.save()
    grp = mgmt.log_groups.new("databases", name="Databases")
    grp.save()

    # App-service-owned resources
    for env in mgmt.environments.list():
        print(env.id)
    mgmt.contexts.register([...])
    settings = mgmt.account_settings.get()
```

The management client takes only `api_key` (plus optional `profile`, `base_domain`, `scheme`, `debug`) — `environment` and `service` have no meaning for CRUD work and are deliberately rejected.

For async usage, swap `SmplClient` → `AsyncSmplClient` and `SmplManagementClient` → `AsyncSmplManagementClient`; method bodies become `await`-able:

```python
from smplkit import AsyncSmplClient, AsyncSmplManagementClient

async with AsyncSmplClient(api_key="sk_api_...", environment="prod", service="svc") as client:
    db = await client.config.get("database")

async with AsyncSmplManagementClient(api_key="sk_api_...") as mgmt:
    cfg = await mgmt.configs.get("my_service")
    configs = await mgmt.configs.list()
```

### Which client should I use?

- **Inside a request handler / running service** → `SmplClient`. You want lazy-fetched runtime state, the context registration loop, metrics, and the live-update websocket.
- **In a setup script / CI job / admin CLI / seeder** → `SmplManagementClient`. No runtime side effects, no auto-registered service rows leaking into target accounts, no websocket dangling open.

The two clients can be used together in the same process — e.g. a runtime app that occasionally needs to reach into the management API for an admin endpoint.

### Management namespaces

The `SmplManagementClient` exposes eight flat namespaces (one per resource family):

| Namespace | Resource |
|-----------|----------|
| `mgmt.contexts` | Context instances (register / list / get / delete) |
| `mgmt.context_types` | Targeting-rule entity schemas |
| `mgmt.environments` | Environments (built-ins + AD_HOC) |
| `mgmt.account_settings` | Per-account settings |
| `mgmt.configs` | Smpl Config CRUD |
| `mgmt.flags` | Smpl Flags CRUD |
| `mgmt.loggers` | Smpl Logging logger CRUD |
| `mgmt.log_groups` | Smpl Logging log-group CRUD |

## Configuration

All settings are resolved from three sources, in order of precedence:

1. **Constructor arguments** — highest priority, always wins.
2. **Environment variables** — e.g. `SMPLKIT_API_KEY`, `SMPLKIT_ENVIRONMENT`.
3. **Configuration file** (`~/.smplkit`) — INI-format with profile support.
4. **Defaults** — built-in SDK defaults.

### Configuration File

The `~/.smplkit` file supports a `[common]` section (applied to all profiles) and named profiles:

```ini
[common]
environment = production
service = my-app

[default]
api_key = sk_api_abc123

[local]
base_domain = localhost
scheme = http
api_key = sk_api_local_xyz
environment = development
debug = true
```

### Constructor Examples

```python
# Use a named profile
client = SmplClient(profile="local")

# Or configure explicitly
client = SmplClient(
    api_key="sk_api_...",
    environment="production",
    service="my-service",
)
```

For the complete configuration reference, see the [Configuration Guide](https://docs.smplkit.com/getting-started/configuration).

## Error Handling

All SDK errors extend `SmplError`:

```python
from smplkit import SmplError, SmplNotFoundError

try:
    config = mgmt.configs.get("nonexistent")
except SmplNotFoundError:
    print("Config not found")
except SmplError as e:
    print(f"SDK error: {e}")
```

| Exception              | Cause                        |
|------------------------|------------------------------|
| `SmplNotFoundError`    | Resource not found           |
| `SmplConflictError`    | Conflict (e.g., has children)|
| `SmplValidationError`  | Validation error             |
| `SmplTimeoutError`     | Request timed out            |
| `SmplConnectionError`  | Network connectivity issue   |
| `SmplError`            | Any other SDK error          |

## Debug Logging

Set `SMPLKIT_DEBUG=1` to enable verbose diagnostic output to stderr. This is useful for troubleshooting real-time level changes, WebSocket connectivity, and SDK initialization. Debug output bypasses the managed logging framework and writes directly to stderr.

```bash
SMPLKIT_DEBUG=1 python my_app.py
```

Accepted values: `1`, `true`, `yes` (case-insensitive). Any other value (or unset) disables debug output.

## Documentation

- [Getting Started](https://docs.smplkit.com/getting-started)
- [Python SDK Guide](https://docs.smplkit.com/sdks/python)
- [API Reference](https://docs.smplkit.com/api)

## License

MIT
