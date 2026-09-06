# Contract: async entry points on `Nornir`, `Task` and `Host`

**Feature**: 001-asyncio-runner | Protocols: [protocols.py](protocols.py) | Errors: [errors.md](errors.md)

Everything below is additive. No existing member changes signature, default or behaviour,
with the single exception noted under `Nornir.run`.

## `nornir.core.Nornir`

```python
async def arun(
    self,
    task: Callable[..., Coroutine[Any, Any, Any]],
    raise_on_error: bool | None = None,
    on_good: bool = True,
    on_failed: bool = False,
    name: str | None = None,
    **kwargs: Any,
) -> AggregatedResult
```

- Same arguments and same return shape as `run`. Applies `raise_on_error` (argument, else
  `config.core.raise_on_error`) and updates `data.failed_hosts` identically.
- Order of operations: task-kind check → runner-kind check → `processors.task_started` →
  host selection → `await runner.arun(task, hosts)` → `raise_on_error` / `failed_hosts` →
  `processors.task_completed`.
- Raises `SyncTaskOnAsyncRunError` if `task` is not a coroutine function;
  `RunnerNotAsyncError` if the runner has no coroutine-function `arun`. Both before any event.
- Cancellation while awaiting the runner: propagates `asyncio.CancelledError`; no result, no
  `failed_hosts` change, no `task_completed`.
- Zero selected hosts: logs the existing warning, returns an empty `AggregatedResult`.

```python
async def aclose_connections(self, on_good: bool = True, on_failed: bool = False) -> None
```

- Runs an `async def` task through `arun` that awaits `task.host.aclose_connections()`, so
  processors observe it and `on_good`/`on_failed` apply.

```python
async def __aenter__(self) -> Nornir
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None   # awaits aclose_connections(on_good=True, on_failed=True)
```

`Nornir.run` (existing): unchanged signature. **One behavioural change**: a coroutine-function
`task` now raises `AsyncTaskOnSyncRunError` before `task_started` instead of recording the
un-awaited coroutine as a successful result. On an `AsyncioRunner`, `run`, `close_connections`
and `__exit__` raise `RunnerNotSyncError` (from the runner's `run`).

## `nornir.core.task.Task`

```python
async def astart(self, host: Host) -> MultiResult
```

- Async twin of `start`: sets `host`, emits `task_instance_started` (or the subtask event),
  awaits `self.task(self, **self.params)`, converts a non-`Result` return into `Result`,
  converts `NornirSubTaskError` / `Exception` into a failed `Result` (with `traceback.format_exc()`
  for the latter), inserts at index 0, emits `*_instance_completed`, returns `self.results`.
- `BaseException` (including `asyncio.CancelledError`) propagates without recording.

```python
async def arun(self, task: Callable[..., Coroutine[Any, Any, Any]], **kwargs: Any) -> MultiResult
```

- Async twin of `run`: builds the subtask with `parent_task=self` and inherited
  `severity_level`, awaits its `astart(self.host)`, appends the result to `self.results`,
  raises `NornirSubTaskError(task=run_task, result=r)` if it failed. Raises
  `SyncTaskOnAsyncRunError` first if `task` is not a coroutine function.

`Task.run` (existing): unchanged for `def` subtasks, including when called from inside an
`async def` task (runs inline). Raises `AsyncTaskOnSyncRunError` for a coroutine-function
subtask, pointing to `await task.arun(...)`.

## `nornir.core.inventory.Host`

```python
async def aget_connection(self, connection: str, configuration: Config) -> Any
async def aopen_connection(
    self,
    connection: str,
    configuration: Config,
    hostname: str | None = None,
    username: str | None = None,
    password: str | None = None,
    port: int | None = None,
    platform: str | None = None,
    extras: dict[str, Any] | None = None,
    default_to_host_attributes: bool = True,
) -> AsyncConnectionPlugin
async def aclose_connection(self, connection: str) -> None
async def aclose_connections(self) -> None
```

- Same parameter resolution as the sync methods (`get_connection_parameters`, host attribute
  defaults). Same cache: `self.connections`, keyed by name.
- `aget_connection`: returns the cached connection if the name is open (whichever path opened
  it); otherwise awaits `aopen_connection` and returns `.connection`. Raises
  `ConnectionAlreadyOpen` if the name is currently being opened by another coroutine.
- `aopen_connection`: raises `ConnectionAlreadyOpen` if open or opening;
  `ConnectionPluginNotAsyncError` if the plugin has no coroutine-function `aopen`.
- `aclose_connection`: `ConnectionNotOpen` if absent; awaits `aclose` if the plugin has async
  members, otherwise calls `close`.
- `aclose_connections`: closes every open connection of either kind; never an error when
  nothing is open.

Sync methods (existing) gain two guards: `open_connection` (hence `get_connection`) raises
`ConnectionPluginNotSyncError` for a plugin without a callable `open`; `close_connection` raises
it for a stored plugin without a callable `close`.

## `nornir.plugins.runners.AsyncioRunner`

See [protocols.py](protocols.py). Registered as `asyncio`; `num_workers` default 20.

## Processor events on the async path

Identical sequence and arguments to the sync path: `task_started(task)` once;
`task_instance_started(task, host)` / `task_instance_completed(task, host, result)` once per
host; `subtask_instance_*` per subtask; `task_completed(task, result)` once. Processor hooks are
called synchronously on the event loop (known limitation, #1090).
