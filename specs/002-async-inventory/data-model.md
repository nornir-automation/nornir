# Data Model: Async Inventory

**Feature**: 002-async-inventory | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

This feature adds no persistent data. The entities below are the public contracts,
registries and the resolution state that `load_inventory` and `aload_inventory` build on
the way to an `Inventory`. Signatures are in [contracts/protocols.py](contracts/protocols.py).

## Entities

### CapabilityInventoryPlugin (new protocol)

| Member | Kind | Rule |
|---|---|---|
| `__init__(**options)` | constructor | Receives `inventory.options`. MUST NOT perform I/O. |
| `get_capabilities()` | sync method | Returns exactly `{"sync"}`, `{"asyncio"}` or `{"sync", "asyncio"}` as a `frozenset[InventoryCapability]`. No I/O. Stable for the instance's lifetime. |
| `load()` | sync method | Required when `"sync"` is declared. Returns `Inventory`. |
| `aload()` | coroutine method | Required when `"asyncio"` is declared. Returns `Inventory`. MUST NOT block the event loop. |

Sub-protocols for typing, mirroring spec 001: `SyncCapabilityInventoryPlugin`,
`AsyncCapabilityInventoryPlugin`, `DualCapabilityInventoryPlugin`.

**Validation** (R2), applied after construction and before any loading method:
`get_capabilities` accessible and synchronous → call succeeds → value is one of the three
valid `frozenset`s → declared operations present with the right kind (sync callable /
coroutine function). Any failure raises `InventoryPluginContractError(name, reason)`.

### AsyncTransformFunction (new protocol)

`async def __call__(self, host: Host, **kwargs: Any) -> None`. Same arguments as
`TransformFunction`; receives `inventory.transform_function_options`. MUST be an
`async def` function (detected with `inspect.iscoroutinefunction`, R5).

### Registries

| Register | Type | Entry-point group | Dictionary |
|---|---|---|---|
| `InventoryPluginRegister` (existing) | `PluginRegister[type[InventoryPlugin]]` | `nornir.plugins.inventory` | shared legacy dict (unchanged) |
| `CapabilityInventoryPluginRegister` (new) | `PluginRegister[type[CapabilityInventoryPlugin]]` | `nornir.plugins.capability_inventory` | own dict |
| `TransformFunctionRegister` (existing) | `PluginRegister[TransformFunction]` | `nornir.plugins.transform_function` | shared legacy dict (unchanged) |
| `AsyncTransformFunctionRegister` (new) | `PluginRegister[AsyncTransformFunction]` | `nornir.plugins.async_transform_function` | own dict |

The legacy registries share one dictionary because `PluginRegister.available` is a class
attribute (research R6). The new registries are given their own dictionary at module level.

### Resolved inventory source (private)

The result of looking up `inventory.plugin`, used by both loaders.

| Variant | Produced when | Loaded by `InitNornir` | Loaded by `AInitNornir` |
|---|---|---|---|
| legacy | name only in `InventoryPluginRegister` | `load()` | `load()` in worker thread |
| capability `{"sync"}` | name only in capability register | `load()` | `load()` in worker thread |
| capability `{"asyncio"}` | name only in capability register | `InventoryPluginNotSyncError` | `await aload()` |
| capability dual | name only in capability register | `load()` | `await aload()` |
| ambiguous | name in both registers | `InventoryPluginAmbiguousError` | same |
| missing | name in neither | `PluginNotRegistered` | same |

### Resolved transform (private)

| Variant | Produced when | `InitNornir` | `AInitNornir` |
|---|---|---|---|
| none | `inventory.transform_function` empty | — | — |
| sync | resolved callable is not a coroutine function | called per host | called per host in worker thread |
| async | resolved callable is a coroutine function | `TransformFunctionNotSyncError` | awaited per host, sequentially |
| ambiguous | name in both transform registers | `TransformFunctionAmbiguousError` | same |
| missing | name in neither | `PluginNotRegistered` | same |

## Order of operations

Both loaders follow the same order; each step can stop the load with the error shown.

1. Auto-register both inventory registers; resolve the inventory source
   (ambiguous / missing).
2. If a transform is configured: auto-register both transform registers; resolve and
   classify it (ambiguous / missing). `InitNornir` raises `TransformFunctionNotSyncError`
   here for an async transform.
3. Construct the plugin with `inventory.options`.
4. For a capability plugin: validate the declaration (contract error). `InitNornir` raises
   `InventoryPluginNotSyncError` here for an asyncio-only plugin.
5. Load: `load()` or `aload()` per the table above.
6. Apply the transform to every host in inventory order.
7. Return the `Inventory`.

No loading method and no transform runs before step 5, which satisfies FR-007, FR-013,
FR-014, FR-015 and SC-005.

## State transitions

`AInitNornir` has one cancellable state per await point:

```text
start ─► resolving ─► constructing ─► validating ─► loading ─► transforming ─► done
                                                      │             │
                                         cancel ──────┴─────────────┴──► CancelledError
```

- Cancelled while awaiting `aload()` or an async transform: cancellation is delivered to
  the plugin's or transform's coroutine.
- Cancelled while awaiting the worker thread: `CancelledError` is raised immediately; the
  thread runs to completion and its result is discarded.
- Steps before `loading` have no await point.
