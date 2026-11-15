# Contract: Errors

**Feature**: 004-typed-operations | [Plan](../plan.md)

All in `nornir/core/exceptions.py`.

```text
Exception
└── OperationError
    ├── OperationInputError
    ├── OperationOutputError
    ├── OperationNotRegisteredError
    ├── OperationAlreadyRegisteredError
    ├── OperationConnectionNotSetError
    ├── OperationEntryPointError
    └── OperationContractNotFoundError
```

- Fields are plain strings, so each class defines `__reduce__` and pickles, as the spec 003
  errors do.
- Errors raised for one host are carried by that host's `Result(failed=True,
  exception=...)`. The other hosts continue.
- Errors raised before the run return no stream or handle.

| Class | Raised | Fields | Message example |
|---|---|---|---|
| `OperationInputError` | Before the run (static `params`), or for one host (callable `params`) | `operation`, `reason`, `host_name: str \| None` | `invalid input for operation 'get_config': unexpected field 'sanitize' (did you mean 'sanitized'?)` / `invalid input for operation 'backup' on host 'r2': the params callable raised KeyError('path')` |
| `OperationOutputError` | For one host | `operation`, `task_name`, `returned_type`, `expected_type`, `host_name` | `task 'ios_napalm_get_config' for operation 'get_config' on host 'r1' returned 'dict', expected 'GetConfigOutput'.` |
| `OperationNotRegisteredError` | For one host; also by `OperationRegistry.get` | `operation`, `platform: str \| None`, `connection`, `registered: tuple[str, ...]`, `host_name: str \| None` | `no task registered for operation 'get_config' on platform 'panos' with connection 'napalm'. Registered for 'get_config': eos.napalm, ios.napalm.` / `host 'fw-1' has no platform, so no task can be selected for operation 'get_config'.` |
| `OperationAlreadyRegisteredError` | `register`, entry-point loading, Operation class definition | `operation`, `key: str \| None`, `existing: str`, `new: str` | `cannot register myproject.tasks.ios_get_config for get_config.ios.napalm: distribution 'nornir_napalm' (entry point 'get_config.ios.napalm') already registered it. Pass replace=True to override.` / `operation name 'get_config' is already defined by pkg_a.ops.GetConfig; cannot define pkg_b.ops.GetConfig.` |
| `OperationConnectionNotSetError` | Before the run | `operation` | `no connection for operation 'get_config': pass connection= or set core.operation_connection.` |
| `OperationEntryPointError` | Entry-point loading | `distribution`, `entry_point`, `reason` | `distribution 'nornir_foo' declares implementation entry point 'get_config.ios' in 'nornir.plugins.operation_tasks': the name must be '<operation>.<platform>.<connection>'.` |
| `OperationContractNotFoundError` | Before the run (`run_operation("name", ...)`) | `operation`, `registered: tuple[str, ...]` | `no Operation named 'get_cfg' is defined. Known Operations: get_config, get_facts.` |

## Reused errors

| Class | When, for Operations |
|---|---|
| `AsyncTaskOnSyncRunError` | For one host: an `async def` implementation selected on `run_operation` / `submit_operation`. New optional arguments `operation` and `host_name` add "(selected for operation 'get_config' on host 'r1')" to the message. |
| `SyncTaskOnAsyncRunError` | For one host: a `def` implementation selected on `arun_operation` / `asubmit_operation`. Same optional arguments. |
| `RunnerCapabilityError` | Before the run: the runner does not support streaming (`run_operation`) or background runs (`submit_operation`). Capability names `run_operation`, `submit_operation`, `arun_operation`, `asubmit_operation`. |
| `RunnerNotSyncError` / `RunnerNotAsyncError` | Before the run: the runner kind does not match the method. |
| `ValueError` | `OperationRegistry.register` with an empty or `None` platform or connection. |
| `TypeError` | Defining an Operation subclass whose type arguments are not classes. |
