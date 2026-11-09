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

A package that must still support Nornir releases without this feature can keep its
legacy registration under the same name, pointing to the same class. Nornir releases with
this feature then use the capability registration. Registering one name in both groups for
two different classes raises `InventoryPluginAmbiguousError`.

## Lookup of `inventory.plugin`

Both `InitNornir` and `AInitNornir` call `auto_register()` on `InventoryPluginRegister`.
From `nornir.plugins.capability_inventory`, they load only the entry points named
`inventory.plugin` (FR-020). Then:

| In legacy | In capability | Result |
|---|---|---|
| yes, same class | yes | capability plugin |
| yes, different class | yes | `InventoryPluginAmbiguousError` |
| yes | no | legacy plugin |
| no | yes | capability plugin |
| no | no | `PluginNotRegistered` |

## Lookup of `inventory.transform_function`

Only when it is set. Both entry points call `auto_register()` on
`TransformFunctionRegister` and load only the entry points named
`inventory.transform_function` from `nornir.plugins.async_transform_function`, then apply
the same table with `TransformFunctionAmbiguousError`. The resolved callable is then
classified with `inspect.iscoroutinefunction` on the callable and on its class's
`__call__`, not by registry (research R5).

When the name is in neither register, the inventory plugin is loaded first and the lookup
runs again, because a plugin can register its transform function while it loads. The name
is then resolved, classified and checked after `load()`; `PluginNotRegistered` is raised
only if it is still missing.

## Configuration

No configuration key is added or changed. `inventory.plugin`, `inventory.options`,
`inventory.transform_function` and `inventory.transform_function_options` keep their
meaning; the entry point decides how the resolved plugin and transform are called.
