# Data Model: Operations, Typed Actions Across Vendors

**Feature**: 004-typed-operations | [Plan](plan.md) | [Research](research.md)

All state is in memory, per process. Nothing is persisted.

## Operation (contract)

A class that subclasses `Operation[InT, OutT]` and defines `name`.

| Attribute | Type | Source | Rule |
|---|---|---|---|
| `name` | `ClassVar[str]` | set by the author | Unique per process (FR-018). Must not contain `.` when declared through an entry point (FR-015a). |
| `input_model` | `ClassVar[type]` | read from the first type argument (R3) | Must be a class. |
| `output_model` | `ClassVar[type]` | read from the second type argument (R3) | Must be a class. |

Lifecycle:

1. **Defined**: `__init_subclass__` reads the models and registers the class under `name`.
2. **Re-defined** (same `__module__` and `__qualname__`): replaces the registered class (R11).
3. **Conflicting** (same `name`, different module or qualified name): raises
   `OperationAlreadyRegisteredError`.

A subclass without `name` is an intermediate base: it is not registered.

## Registration (implementation)

One per `(operation, platform, connection)` key.

| Field | Type | Rule |
|---|---|---|
| `operation` | `str` | The Operation name. The contract does not have to be known yet (FR-020). |
| `platform` | `str` | Not `None`, not empty (FR-013). Compared as written; no normalisation. |
| `connection` | `str` | Not empty. |
| `task` | `Callable[..., Any]` | A plain task: `def task(task, params: In) -> Out \| Result[Out]`, or its `async def` form. |
| `kind` | `Literal["sync", "async"]` | Computed from `task` with `_is_async_task` (R14). |
| `source` | `RegistrationSource` | Recorded when registered (FR-017). |

Rules:

- The same `task` object under the same key again: accepted, no change.
- A different `task` under a taken key: `OperationAlreadyRegisteredError` naming both
  sources, unless `replace=True` (FR-016). Entry points never replace.

## RegistrationSource

| Field | Type | Set for |
|---|---|---|
| `kind` | `Literal["entry_point", "call"]` | both |
| `distribution` | `str \| None` | entry point: `entry_point.dist.name` |
| `entry_point` | `str \| None` | entry point: the entry-point name, for example `get_config.ios.napalm` |
| `module` | `str` | both: `task.__module__` |
| `qualname` | `str` | both: `task.__qualname__` |

`str(source)` gives the form used in error messages, for example
`distribution 'nornir_napalm' (entry point 'get_config.ios.napalm')` or
`myproject.tasks.ios_get_config`.

## OperationInfo (listing)

Returned by `OperationRegistry.operations()`, one per known Operation name, sorted by name.

| Field | Type | Rule |
|---|---|---|
| `name` | `str` | |
| `operation` | `type[Operation[Any, Any]] \| None` | `None` when implementations exist but no contract is known. |
| `input_model` | `type \| None` | From the contract. |
| `output_model` | `type \| None` | From the contract. |
| `implementations` | `tuple[Registration, ...]` | Sorted by `(platform, connection)`. Empty when no implementation is installed. |

## OperationRegistry state

| State | Type | Notes |
|---|---|---|
| contracts | `dict[str, type[Operation[Any, Any]]]` | Filled when classes are defined and when contract entry points load. |
| registrations | `dict[tuple[str, str, str], Registration]` | Filled by `register()` and implementation entry points. |
| loaded | `bool` | Set once both entry-point groups loaded without error (R9). |
| lock | `threading.RLock` | Guards all three. Reentrant, because loading an entry point imports a module that defines an Operation class, which registers it. |

## Per-run objects

### `_OperationTask(Task)` (private)

Created once by `run_operation`; each runner gives each host a copy.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | The Operation name, so processors and `AggregatedResult` use it. |
| `operation` | `type[Operation]` | Its `name` is dispatch key part 1; its `input_model` builds per-host inputs; its `output_model` is checked by `_check_result`. |
| `connection` | `str` | Dispatch key, part 3. Resolved before the run (FR-005). |
| `params_source` | `In \| Callable[[Host], In]` | A validated static input, or the per-host callable. |
| `per_host` | `bool` | Whether `params_source` is the per-host callable. |

The synchronous or asynchronous path is passed to `_resolve_call` by the method that
calls it (`_start_steps` or `_acall`), so it is not stored.

Per host, in `_resolve_call` (all inside the existing `try`, so any error fails only that host):

```text
host started
  └─ platform is None?           → OperationNotRegisteredError ("host has no platform")
  └─ registration found?         → no: OperationNotRegisteredError (lists registered keys)
  └─ kind matches path?          → no: AsyncTaskOnSyncRunError / SyncTaskOnAsyncRunError
  └─ params callable?            → yes: call it, validate → error: OperationInputError
  └─ set task.task, task.params  → implementation called by the existing Task line
host finished
  └─ _check_result               → not failed and wrong type: OperationOutputError
```

### Generic run objects

| Class | Change |
|---|---|
| `Result` | `Generic[T]`, `T` defaults to `Any` for the type checker only (R1). `result: T`. |
| `RunStream`, `RunHandle`, `AsyncRunStream`, `AsyncRunHandle` | `Generic[T]`; `results()` yields `Result[T]`; `events()` yields `PartialResult \| Result[T]`. |
| `MultiResult`, `AggregatedResult` | Unchanged; they hold `Result[Any]`. |

## Configuration

| Parameter | Type | Default | Environment variable |
|---|---|---|---|
| `core.operation_connection` | `str` | `""` (unset) | `NORNIR_CORE_OPERATION_CONNECTION` |
