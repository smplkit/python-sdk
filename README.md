# smplkit Python SDK

The official Python SDK for [smplkit](https://smplkit.com) — simple application infrastructure for developers.

## Installation

```bash
pip install smplkit-sdk
```

## Requirements

- Python 3.10+

## Quick Start

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

```python
client = SmplClient(api_key="sk_api_...")
```

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
