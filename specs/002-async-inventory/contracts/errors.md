# Contract: named errors

**Feature**: 002-async-inventory | Target: `nornir/core/exceptions.py`

Each class stores its constructor arguments as attributes and its message names the plugin
or transform and the fix. All are raised before any loading method or transform runs.

## Execution-mode mismatches (base `SyncAsyncMismatchError`)

| Class | Constructor | Raised by | Message guidance |
|---|---|---|---|
| `InventoryPluginNotSyncError` | `plugin_name: str` | `InitNornir` / `load_inventory` when the capability plugin declares only `asyncio` | The plugin only supports asynchronous loading; use `nr = await AInitNornir(...)`, or ask the plugin author for synchronous support |
| `TransformFunctionNotSyncError` | `transform_name: str` | `InitNornir` / `load_inventory` when the resolved transform is a coroutine function, from either registry | The transform is defined with `async def`; use `nr = await AInitNornir(...)`, or define a synchronous transform |

`AInitNornir` never raises a "not async" error: it accepts every plugin and transform.

## Registry and contract validation (base `Exception`)

Changing the entry point does not repair these, so they are not mismatch errors.

| Class | Constructor | Conditions | Message guidance |
|---|---|---|---|
| `InventoryPluginAmbiguousError` | `plugin_name: str` | Name in both `InventoryPluginRegister` and `CapabilityInventoryPluginRegister`, even for the same class | Name both registries; remove one registration or rename the plugin |
| `TransformFunctionAmbiguousError` | `transform_name: str` | Name in both `TransformFunctionRegister` and `AsyncTransformFunctionRegister` | Name both registries; remove one registration or rename the transform |
| `InventoryPluginContractError` | `plugin_name: str, reason: str` | `get_capabilities` inaccessible, async, failing, or returning an invalid value; declared `load` missing or a coroutine function; declared `aload` missing or not a coroutine function | Name the plugin and the failed requirement; chain the original exception when `get_capabilities` raised |

The legacy registries share one dictionary (research R6), so an ambiguity error can also
report a name used by a plugin of another kind (runner, connection). The message names
both registries so the collision is visible.

## Unchanged

`PluginNotRegistered` (name in neither registry of a kind), `PluginAlreadyRegistered`
(same-registry conflicts). Exceptions raised by `load()`, `aload()` or a transform propagate
unchanged, with no `Nornir` object returned. `asyncio.CancelledError` propagates unchanged.

## Precedence

For one call, the first applicable error wins, in this order:

1. `InventoryPluginAmbiguousError` / `PluginNotRegistered` for the inventory plugin
2. `TransformFunctionAmbiguousError` / `PluginNotRegistered` for the transform
3. `TransformFunctionNotSyncError` (`InitNornir` only)
4. `InventoryPluginContractError`
5. `InventoryPluginNotSyncError` (`InitNornir` only)
