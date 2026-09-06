# Data Model: Asyncio Runner

**Feature**: 001-asyncio-runner | **Date**: 2026-09-06 | **Plan**: [plan.md](plan.md)

Nornir is a library, so the "data model" is the set of Python objects the feature adds or
extends, their fields, the invariants they keep, and the state they move through. Signatures are
given in [contracts/](contracts/); this file describes meaning and rules.

## Entities

### AsyncioRunner (new, `nornir/plugins/runners/__init__.py`)

| Field | Type | Meaning |
|---|---|---|
| `num_workers` | `int`, default `20` | Maximum number of hosts in flight at once |

- Satisfies both `RunnerPlugin` (its `run()` always raises `RunnerNotSyncError`) and
  `AsyncRunnerPlugin` (`arun()` does the work).
- Holds no loop-bound state between calls: the semaphore is created inside `arun()`.
- Invariants: `len(result) == len(hosts)`; result keys are host names in the order given;
  at most `num_workers` `astart` coroutines are past the semaphore at any instant; the process
  thread count is unchanged by a run.

### Nornir (extended, `nornir/core/__init__.py`)

New members: `arun`, `aclose_connections`, `__aenter__`, `__aexit__`. Existing members and
their signatures are unchanged. `run` is refactored onto shared private helpers with no
behavioural change, except that an `async def` task now raises `AsyncTaskOnSyncRunError`
before `task_started` instead of recording a coroutine object as a successful result.

Shared state touched by both `run` and `arun`: `data.failed_hosts` (a set of host names in
`GlobalState`), updated only when `raise_on_error` is false, exactly as today.

### Task (extended, `nornir/core/task.py`)

| Field | Set by | Meaning |
|---|---|---|
| `task` | constructor | the user callable (`def` or `async def`) |
| `host` | `_begin` (from `start`/`astart`) | host this copy runs against |
| `results` | `_finish`, `_record_subtask` | `MultiResult`, own result at index 0, subtasks appended |
| `parent_task` | constructor | `None` for a top-level task, the parent for a subtask |

New members: `astart(host) -> MultiResult`, `arun(task, **kwargs) -> MultiResult`.

Validation rules:
- `Task.run(subtask)` raises `AsyncTaskOnSyncRunError` if `subtask` is a coroutine function.
- `Task.arun(subtask)` raises `SyncTaskOnAsyncRunError` if `subtask` is not a coroutine function.
- Both checks happen before the subtask's `*_instance_started` event.
- `Task.run(def_subtask)` inside an `async def` task runs inline on the event loop (FR-009);
  no check or warning is added.

### Host connection cache (extended, `nornir/core/inventory.py`)

| Field | Type | Visibility | Meaning |
|---|---|---|---|
| `connections` | `dict[str, ConnectionPlugin]` | public (existing) | open connections keyed by connection name, regardless of which path opened them |
| `_opening` | `set[str]` | private (new slot) | names whose `aopen` is currently being awaited |

New members: `aget_connection`, `aopen_connection`, `aclose_connection`, `aclose_connections`.

Invariants:
- A name is never in both `connections` and `_opening`.
- `_opening` is empty whenever no `aopen_connection` coroutine is suspended for this host;
  a failed `aopen` removes the name (try/finally).
- The cache is keyed by name only: a connection opened by `get_connection` is returned by
  `aget_connection` for the same name without calling `aopen`, and vice versa.

### AsyncConnectionPlugin (new Protocol, `nornir/core/plugins/connections.py`)

Members `aopen`, `aclose`, `connection`. Same parameters, same order as `open`/`close`. A class
may implement `ConnectionPlugin`, `AsyncConnectionPlugin`, or both; which it implements is
determined by the presence of `open` (callable) and `aopen` (coroutine function). Registration
goes through the existing `ConnectionPluginRegister` under the existing entry-point group.

Rules for authors (documented, not enforced): `aopen` and `aclose` must not block the event
loop; `aclose` must be safe to call more than once.

### AsyncRunnerPlugin (new Protocol, `nornir/core/plugins/runners.py`)

Members `__init__(*args, **kwargs)` and `async def arun(task, hosts) -> AggregatedResult`.
Detected by the presence of a coroutine-function `arun`.

### Named errors (new, `nornir/core/exceptions.py`)

```text
Exception
└── SyncAsyncMismatchError
    ├── SyncTaskOnAsyncRunError        (task_name)
    ├── AsyncTaskOnSyncRunError        (task_name)
    ├── RunnerNotSyncError             (runner_name)
    ├── RunnerNotAsyncError            (runner_name)
    ├── ConnectionPluginNotAsyncError  (connection_name)
    └── ConnectionPluginNotSyncError   (connection_name)
```

Each carries the offending name as an attribute and renders a message that names the entry
point to use instead (see [contracts/errors.md](contracts/errors.md)). `SyncTaskOnAsyncRunError`
also renders `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE`.

### AsyncEcho fixture (new, test-only, `tests/plugins/connections/async_echo.py`)

| Object | Fields | Meaning |
|---|---|---|
| `AsyncEcho` | `_connection: EchoConnection \| None` | the plugin; implements only the async contract |
| `EchoConnection` | `reader: asyncio.StreamReader`, `writer: asyncio.StreamWriter` | what `connection` returns; `send(payload) -> bytes` echoes through the socket |

`aclose` is idempotent: a second call is a no-op. `hostname` and `port` are the only connection
parameters it uses; the others are accepted and ignored, as the contract requires.

## State transitions

### A host's run of a task (per `Task` copy)

```text
created ──_begin(host)──▶ started ──task returns/raises Exception──▶ completed (Result recorded,
                                                                     *_instance_completed emitted)
                              │
                              └──BaseException (e.g. CancelledError)──▶ abandoned (nothing recorded,
                                                                          no completed event)
```

### A run (`Nornir.run` / `Nornir.arun`)

```text
validate task kind ─▶ [arun only: validate runner kind] ─▶ task_started ─▶ select hosts
   ─▶ runner.run / await runner.arun ─▶ raise_on_error | update failed_hosts ─▶ task_completed
```

Cancellation of `arun` while awaiting the runner: every in-flight host coroutine is cancelled
and awaited, `CancelledError` propagates, no step after the runner executes (no result, no
`failed_hosts` change, no `task_completed`).

### A connection slot on a host (per name)

```text
absent ──open() [sync]──────────────────────────────▶ open
absent ──aopen_connection(): add to _opening──▶ opening ──aopen succeeds──▶ open
                                                   │
                                                   └──aopen raises──▶ absent (name discarded)
open ──close() / await aclose()──▶ absent
opening ──concurrent aget_connection / aopen_connection──▶ raises ConnectionAlreadyOpen, slot unchanged
```

## Validation rules (consolidated)

| Surface | Condition | Error |
|---|---|---|
| `Nornir.run(task)` | task is a coroutine function | `AsyncTaskOnSyncRunError` |
| `Nornir.run(task)` | runner is `AsyncioRunner` | `RunnerNotSyncError` (from `AsyncioRunner.run`) |
| `Nornir.arun(task)` | task is not a coroutine function | `SyncTaskOnAsyncRunError` |
| `Nornir.arun(task)` | runner has no coroutine-function `arun` | `RunnerNotAsyncError` |
| `Task.run(subtask)` | subtask is a coroutine function | `AsyncTaskOnSyncRunError` |
| `Task.arun(subtask)` | subtask is not a coroutine function | `SyncTaskOnAsyncRunError` |
| `Host.get_connection` / `open_connection` | plugin has no callable `open` | `ConnectionPluginNotSyncError` |
| `Host.close_connection` | stored plugin has no callable `close` | `ConnectionPluginNotSyncError` |
| `Host.aget_connection` / `aopen_connection` | plugin has no coroutine-function `aopen` | `ConnectionPluginNotAsyncError` |
| `Host.aopen_connection` | name already open or opening | `ConnectionAlreadyOpen` (existing) |
| `Host.aget_connection` | name currently opening | `ConnectionAlreadyOpen` (existing) |
| `Host.aclose_connection` | name not open | `ConnectionNotOpen` (existing) |
