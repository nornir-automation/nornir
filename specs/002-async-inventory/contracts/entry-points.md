# Contract: entry-point groups and lookup

**Feature**: 002-async-inventory

## Groups

| Group | Register | Holds | Status |
|---|---|---|---|
| `nornir.plugins.inventory` | `InventoryPluginRegister` | legacy `InventoryPlugin` classes | unchanged |
| `nornir.plugins.capability_inventory` | `CapabilityInventoryPluginRegister` | `CapabilityInventoryPlugin` classes (sync, asyncio or dual) | new |
| `nornir.plugins.transform_function` | `TransformFunctionRegister` | `TransformFunction` callables | unchanged |
| `nornir.plugins.async_transform_function` | `AsyncTransformFunctionRegister` | `AsyncTransformFunction` callables | new |

A dual plugin registers once, in `nornir.plugins.capability_inventory` (SC-006):

```toml
[project.entry-points."nornir.plugins.capability_inventory"]
my_api_inventory = "my_package.inventory:MyApiInventory"
```

A package that must still support Nornir releases without this feature keeps its legacy
registration under a different name; registering the same name in both groups raises
`InventoryPluginAmbiguousError`.

## Lookup of `inventory.plugin`

Both `InitNornir` and `AInitNornir` call `auto_register()` on both inventory registers, then:

| In legacy | In capability | Result |
|---|---|---|
| yes | yes | `InventoryPluginAmbiguousError` |
| yes | no | legacy plugin |
| no | yes | capability plugin |
| no | no | `PluginNotRegistered` |

## Lookup of `inventory.transform_function`

Only when it is set. Both entry points call `auto_register()` on both transform registers,
then apply the same table with `TransformFunctionAmbiguousError`. The resolved callable is
then classified by `inspect.iscoroutinefunction`, not by registry (research R5).

## Configuration

No configuration key is added or changed. `inventory.plugin`, `inventory.options`,
`inventory.transform_function` and `inventory.transform_function_options` keep their
meaning; the entry point decides how the resolved plugin and transform are called.
