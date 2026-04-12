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

```python
from smplkit import SmplClient

# Option 1: Explicit API key
client = SmplClient(api_key="sk_api_...")

# Option 2: Environment variable (SMPLKIT_API_KEY)
# export SMPLKIT_API_KEY=sk_api_...
client = SmplClient()

# Option 3: Configuration file (~/.smplkit)
# [default]
# api_key = sk_api_...
client = SmplClient()
```

```python
from smplkit import SmplClient

with SmplClient(api_key="sk_api_...") as client:
    # --- Runtime: resolve config values ---
    # Connect and read resolved key/value pairs for your service
    db = client.config.get("database")  # {"host": "...", "port": 5432}

    # --- Management: CRUD operations ---
    # List all configs
    configs = client.config.management.list()

    # Create a new config
    cfg = client.config.management.new("my_service", name="My Service")
    cfg.save()

    # Get a config by id
    cfg = client.config.management.get("my_service")

    # Delete a config
    client.config.management.delete("my_service")

    # --- Flags management ---
    flag = client.flags.management.newBooleanFlag("checkout-v2", default=False)
    flag.save()
    flags = client.flags.management.list()

    # --- Logging management ---
    logger = client.logging.management.new("sql", name="SQL Logger")
    logger.save()
```

For async usage:

```python
from smplkit import AsyncSmplClient

async with AsyncSmplClient(api_key="sk_api_...") as client:
    # Runtime
    db = await client.config.get("database")

    # Management
    cfg = await client.config.management.get("my_service")
    configs = await client.config.management.list()
```

## Configuration

The API key is resolved using the following priority:

1. **Explicit argument:** Pass `api_key` directly to the constructor.
2. **Environment variable:** Set `SMPLKIT_API_KEY`.
3. **Configuration file:** Add `api_key` under `[default]` in `~/.smplkit`:

```ini
# ~/.smplkit

[default]
api_key = sk_api_your_key_here
```

If none of these are set, the SDK raises `SmplError` with a message listing all three methods.

## Error Handling

All SDK errors extend `SmplError`:

```python
from smplkit import SmplError, SmplNotFoundError

try:
    config = client.config.management.get("nonexistent")
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

## Documentation

- [Getting Started](https://docs.smplkit.com/getting-started)
- [Python SDK Guide](https://docs.smplkit.com/sdks/python)
- [API Reference](https://docs.smplkit.com/api)

## License

MIT
