# Contract: Entry Points and Configuration

**Feature**: 004-typed-operations | [Plan](../plan.md)

## Entry-point groups

| Group | Entry-point name | Value | Effect |
|---|---|---|---|
| `nornir.plugins.operations` | The Operation name, for example `get_config` | The Operation class | Imports the module, which registers the class (research R3). The loader checks that the class's `name` equals the entry-point name, otherwise `OperationEntryPointError`. |
| `nornir.plugins.operation_tasks` | `<operation>.<platform>.<connection>`, for example `get_config.ios.napalm` | The task | Registers the task with `replace=False` and an `entry_point` source. A name that does not split into exactly three non-empty parts raises `OperationEntryPointError`. |

Example `pyproject.toml` of an implementation package:

```toml
[project.entry-points."nornir.plugins.operations"]
get_config = "nornir_ops_core.config:GetConfig"

[project.entry-points."nornir.plugins.operation_tasks"]
"get_config.ios.napalm" = "nornir_napalm.operations:ios_napalm_get_config"
"get_config.eos.napalm" = "nornir_napalm.operations:eos_napalm_get_config"
```

## Loading

- Both groups are read on the first call to `OperationRegistry.get`, `contract`,
  `operations` or `load`, and therefore on the first
  `run_operation`, `submit_operation`, `arun_operation` or `asubmit_operation` of the
  process. `InitNornir` does not load them (research R9).
- Each group is read once per process. An entry point that cannot be loaded does not stop
  the others. The error names the distribution and is recorded:
  - for the key `<operation>.<platform>.<connection>` of an implementation that cannot be
    imported or conflicts with another registration: looking up that key raises it, so
    only the hosts of that platform fail;
  - for the Operation name of a contract, or of an implementation whose name is malformed:
    looking up the name raises it.

  `OperationRegistry.load()` raises the first recorded error each time it is called.
- `register(..., replace=True)` and `deregister()` do not load the entry points. An entry
  point for a key that one of them set is skipped, and its module is not imported. A
  package module can call `register()` while it is imported.
- The source recorded for an entry point is `entry_point.dist.name`, the entry point's name,
  and the module and qualified name of the task.

## Configuration

| Section | Parameter | Type | Default | Environment variable |
|---|---|---|---|---|
| `core` | `operation_connection` | `str` or unset | unset | `NORNIR_CORE_OPERATION_CONNECTION` |

```yaml
core:
  operation_connection: napalm
```

The `connection=` argument of a call overrides it. When neither is set, the call raises
`OperationConnectionNotSetError`.
