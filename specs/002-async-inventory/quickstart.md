# Quickstart: validating async inventory

**Feature**: 002-async-inventory | **Contracts**: [contracts/](contracts/) | **Data model**: [data-model.md](data-model.md)

Runnable checks that show the feature works end to end. Each scenario names the
requirement or success criterion it proves.

## Prerequisites

```bash
uv sync --locked
```

Spec 001 (`specs/001-asyncio-runner`) is merged into the branch, so
`SyncAsyncMismatchError` and the asyncio runner exist.

## 1. Automated gates

```bash
make pytest                                            # all tests, including the new ones
uv run pytest tests/core/test_async_inventory.py tests/core/test_capability_inventory.py tests/core/test_async_transforms.py -v
make tests                                             # ruff, mypy, nbval, pytest, docs
```

Expected: everything passes, with no change to existing tests (SC-004).

## 2. Existing plugin from a running loop (User Story 1, SC-001, SC-002, SC-003)

Using the existing test inventory under `tests/inventory_data/`:

```python
import asyncio
from nornir import AInitNornir, InitNornir

OPTIONS = {
    "plugin": "SimpleInventory",
    "options": {
        "host_file": "tests/inventory_data/hosts.yaml",
        "group_file": "tests/inventory_data/groups.yaml",
        "defaults_file": "tests/inventory_data/defaults.yaml",
    },
}

async def main() -> None:
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0)

    t = asyncio.create_task(ticker())
    nr = await AInitNornir(inventory=OPTIONS)
    t.cancel()
    sync_nr = InitNornir(inventory=OPTIONS)
    assert nr.inventory.dict() == sync_nr.inventory.dict()
    print("hosts:", len(nr.inventory.hosts), "ticks during load:", ticks)

asyncio.run(main())
```

Expected: the inventories are equal and `ticks` is greater than zero.

## 3. Errors for unsupported combinations (SC-005)

With an asyncio-only capability plugin registered as `async_only` and an `async def`
transform registered as `async_enrich` (both defined in the test module):

| Call | Expected |
|---|---|
| `InitNornir(inventory={"plugin": "async_only"})` | `InventoryPluginNotSyncError`; message names `AInitNornir`; `aload` not called |
| `InitNornir(inventory={"plugin": "SimpleInventory", ..., "transform_function": "async_enrich"})` | `TransformFunctionNotSyncError`; `load` not called |
| a name registered in both inventory registers, either entry point | `InventoryPluginAmbiguousError` |
| `get_capabilities()` returns `frozenset()` | `InventoryPluginContractError` |

## 4. Dual plugin and single registration (User Story 2, SC-006)

Covered by `tests/core/test_capability_inventory.py`: a dual plugin advertised once in
`nornir.plugins.capability_inventory` through a patched `importlib.metadata.entry_points`
is loaded with `aload()` by `AInitNornir` and with `load()` by `InitNornir`.

## 5. Cancellation (FR-017, SC-007)

Covered by the cancellation test: `AInitNornir` is cancelled while a synchronous `load()`
waits on a `threading.Event`. Expected: `CancelledError` within a short timeout; the event
is then set inside the same coroutine so the worker thread exits before `asyncio.run()`
waits for it.

## 6. Documentation

```bash
make nbval   # executes docs/howto/async_inventory.ipynb
make docs    # builds the plugin author guide; commit anything regenerated under docs/api/
```
