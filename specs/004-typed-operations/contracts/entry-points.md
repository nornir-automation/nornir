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

- Both groups are read by `OperationRegistry.load()` on the first call to
  `OperationRegistry.get` or `OperationRegistry.operations`, and therefore on the first
  `run_operation`, `submit_operation`, `arun_operation` or `asubmit_operation` of the
  process. `InitNornir` does not load them (research R9).
- Loading is idempotent. If it raises, nothing is marked as loaded and the next call tries
  again.
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
