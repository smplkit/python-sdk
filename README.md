# smplkit Python SDK

[![PyPI Version](https://img.shields.io/pypi/v/smplkit-sdk)](https://pypi.org/project/smplkit-sdk/) [![Build](https://github.com/smplkit/python-sdk/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/smplkit/python-sdk/actions) [![License](https://img.shields.io/pypi/l/smplkit-sdk)](LICENSE) [![Docs](https://img.shields.io/badge/docs-docs.smplkit.com-blue)](https://docs.smplkit.com)

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
    # Get a config by key
    config = client.config.get(key="user_service")

    # List all configs
    configs = client.config.list()

    # Create a config
    new_config = client.config.create(
        name="My Service",
        key="my_service",
        description="Configuration for my service",
        values={"timeout": 30, "retries": 3},
    )

    # Delete a config
    client.config.delete(new_config.id)
```

For async usage:

```python
from smplkit import AsyncSmplClient

async with AsyncSmplClient(api_key="sk_api_...") as client:
    config = await client.config.get(key="user_service")
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
    config = client.config.get(key="nonexistent")
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
