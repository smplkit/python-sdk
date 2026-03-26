# smplkit SDK Examples

Runnable examples demonstrating the [smplkit Python SDK](https://github.com/smplkit/python-sdk).

> **Note:** These examples require valid smplkit credentials and a live environment — they are not self-contained demos.

## Prerequisites

1. Install the SDK:

   ```bash
   pip install smplkit-sdk
   ```

2. A valid smplkit API key (create one in the [smplkit console](https://www.smplkit.com)).
3. At least one config created in your smplkit account (every account comes with a `common` config by default).

## Config Showcase

**File:** [`config_showcase.py`](config_showcase.py)

An end-to-end walkthrough of the Smpl Config SDK covering:

- **Client initialization** — `AsyncSmplClient` (and sync `SmplClient`)
- **Management-plane CRUD** — create, update, list, and delete configs
- **Environment overrides** — per-environment value layering
- **Multi-level inheritance** — child → parent → common deep-merge resolution
- **Runtime value resolution** — `connect()`, `get()`, typed accessors (`get_str`, `get_int`, `get_bool`)
- **Real-time updates** — WebSocket-driven cache invalidation and change listeners
- **Manual refresh** — force re-fetch via `refresh()`
- **Async context manager** — `async with config.connect(...) as runtime:`

### Running

```bash
export SMPLKIT_API_KEY="sk_api_..."
python examples/config_showcase.py
```

The script creates temporary configs, exercises every SDK feature, then cleans up after itself.
