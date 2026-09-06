# Contract: named errors

**Feature**: 001-asyncio-runner | Module: `nornir/core/exceptions.py`

All six errors subclass `SyncAsyncMismatchError(Exception)` so an application can catch the
family. Each is raised **before any per-host processor event** (SC-004). Message wording is
free at implementation time but must contain the pointers in the last column.

| Class | Constructor argument | Raised at | Message must say |
|---|---|---|---|
| `SyncTaskOnAsyncRunError` | `task_name: str` | `Nornir.arun`, `Task.arun` with a task that is not a coroutine function | define `<task_name>` with `async def`, or run it with a synchronous runner (`serial`, `threaded`); synchronous tasks in async runs are tracked in `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE` |
| `AsyncTaskOnSyncRunError` | `task_name: str` | `Nornir.run`, `Task.run` with a coroutine-function task | select the `asyncio` runner and use `await nr.arun(...)` / `await task.arun(...)`, or define `<task_name>` with `def` |
| `RunnerNotSyncError` | `runner_name: str` | `AsyncioRunner.run` (reached through `Nornir.run`, `Nornir.close_connections`, `with nr:` exit) | use `await nr.arun(...)`, `await nr.aclose_connections()`, `async with nr:`; or configure a synchronous runner |
| `RunnerNotAsyncError` | `runner_name: str` | `Nornir.arun`, `Nornir.aclose_connections`, `async with nr:` exit when the runner has no coroutine-function `arun` | use `nr.run(...)`, `nr.close_connections()`, `with nr:`; or select the `asyncio` runner |
| `ConnectionPluginNotAsyncError` | `connection_name: str` | `Host.aget_connection`, `Host.aopen_connection` when the plugin has no coroutine-function `aopen` | the plugin `<connection_name>` has no async members; use `get_connection()` from a synchronous task |
| `ConnectionPluginNotSyncError` | `connection_name: str` | `Host.get_connection`, `Host.open_connection`, `Host.close_connection` when the plugin has no callable `open` / `close` | the plugin `<connection_name>` has no synchronous members; use `aget_connection()` / `aclose_connection()` from an async task |

Module constant:

```python
SYNC_TASKS_IN_ASYNC_RUNS_ISSUE = "https://github.com/nornir-automation/nornir/issues/1085"
```

Replaced by the follow-up issue's URL before merge (spec Assumptions). It is the only place the
number appears in code.

## The seven surfaces (spec edge case) and what they raise

| Surface | Wrong input | Error |
|---|---|---|
| `nr.arun(task)` | `def` task | `SyncTaskOnAsyncRunError` |
| `nr.arun(task)` | sync runner assigned | `RunnerNotAsyncError` |
| `nr.run(task)` | `async def` task | `AsyncTaskOnSyncRunError` |
| `nr.run(task)` | `asyncio` runner assigned | `RunnerNotSyncError` |
| `task.arun(sub)` | `def` subtask | `SyncTaskOnAsyncRunError` |
| `task.run(sub)` | `async def` subtask | `AsyncTaskOnSyncRunError` |
| `nr.close_connections()` / `with nr:` | `asyncio` runner assigned | `RunnerNotSyncError` |
| `host.get_connection(name, cfg)` | plugin has only async members | `ConnectionPluginNotSyncError` |
| `host.aget_connection(name, cfg)` | plugin has only sync members | `ConnectionPluginNotAsyncError` |

Existing exceptions reused unchanged: `ConnectionAlreadyOpen` (also for a concurrent
`aget_connection` on a name that is still opening), `ConnectionNotOpen`, `NornirSubTaskError`,
`NornirExecutionError`.
