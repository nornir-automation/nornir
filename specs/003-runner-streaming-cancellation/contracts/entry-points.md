# Contract: Entry Points

**Feature**: 003-runner-streaming-cancellation | [Plan](../plan.md) | [Types](protocols.py)

## `Nornir` methods

All four take the same selection arguments as `run()`. `run_options` is a keyword
reserved by these new methods only. `run()` and `arun()` keep their signatures (FR-023).

```python
def submit(self, task, raise_on_error=None, on_good=True, on_failed=False,
           name=None, run_options: RunOptions | None = None, **kwargs) -> RunHandle
def run_stream(self, task, raise_on_error=None, on_good=True, on_failed=False,
               name=None, run_options: RunOptions | None = None, **kwargs) -> RunStream
async def asubmit(self, task, raise_on_error=None, on_good=True, on_failed=False,
                  name=None, run_options: RunOptions | None = None, **kwargs) -> AsyncRunHandle
def astream(self, task, raise_on_error=None, on_good=True, on_failed=False,
            name=None, run_options: RunOptions | None = None, **kwargs) -> AsyncRunStream
```

`astream` is a plain method returning an async iterable, so it is used as
`async for event in nr.astream(...)`, without `await`.

### Checks, in order, before any processor event

| Check | `submit` / `run_stream` | `asubmit` / `astream` |
|---|---|---|
| Task mode | async function or async generator → `AsyncTaskOnSyncRunError` | `def` function or generator → `SyncTaskOnAsyncRunError` |
| Runner mode | `AsyncioRunner` → `RunnerNotSyncError` | runner without `aexecute` → `RunnerNotAsyncError` if it also has no `arun`, otherwise `RunnerCapabilityError` |
| Capability | no `execute` → `RunnerCapabilityError` | — |
| Background | `submit` with `supports_background` false → `RunnerCapabilityError` naming `run_stream` | — |
| Options | invalid `RunOptions` values → `ValueError` (raised when the options object is built) | same |

The runner-mode check follows spec 001: a runner that is synchronous only is a mode
error, while a runner that is asynchronous but lacks the new protocol is a capability
error.

### Then

1. `_prepare_run` fires `task_started` and selects the hosts (FR-015, FR-027).
2. A `RunContext` is created with the effective options, and the run deadline starts.
3. `submit`: the background thread starts and the handle is returned. `run_stream`: the
   stream is returned, and the run starts on the first `next()` (`SerialRunner`), or at
   once with the subscription already in place (`ThreadedRunner`). `asubmit`: an asyncio
   task is created on the running loop and the handle is returned. `astream`: same as
   `asubmit`, with a subscription, on the first `__anext__`.

## `RunHandle` / `AsyncRunHandle`

| Member | Behaviour | Requirement |
|---|---|---|
| `id` | Hex identifier, unique per run | FR-005 |
| `done` | True once every host is recorded and the run is finalized | FR-005 |
| `results()` | Final top-level `Result` per host, in completion order; each call replays finished hosts first; any thread | FR-006 |
| `events()` | `PartialResult` and final `Result` events produced after the call | FR-007 |
| `progress()` | `{host_name: latest PartialResult}`; copy | FR-008 |
| `cancel()` | Idempotent, any thread, no effect after the end | FR-015 |
| `result()` | `AggregatedResult` in selection order; raises `NornirExecutionError` when `raise_on_error` applies; sync version takes `timeout` and raises `TimeoutError` | FR-005, FR-028 |

Iterators never raise for a failed host. Leaving a handle iterator early does not cancel
the run (FR-009).

## `RunStream` / `AsyncRunStream`

- Iterating yields `PartialResult` and final `Result` events, from the start of the run.
- Finalizing the iterator before the run ends (`break`, an exception in the loop body)
  cancels the run. On `SerialRunner`, every host is recorded before the statement after
  the loop runs.
- `with` / `async with` cancel on exit if the run has not finished.
- `result()` returns the `AggregatedResult` once the run ends (after the loop, or after
  a cancellation).
- A second iteration raises `RuntimeError`.

## `Task.checkpoint()`

```python
def checkpoint(self) -> None
```

Raises a new `TaskCancelledError` or `TaskTimeoutError` when the host is interrupted or
past a deadline; does nothing otherwise, including outside a run context. The start of
each subtask and every `yield` of a generator task are also checkpoints.

## Runner constructors

```python
SerialRunner(per_host_timeout: float | None = None, timeout: float | None = None)
ThreadedRunner(num_workers: int = 20, per_host_timeout: float | None = None,
               timeout: float | None = None)
AsyncioRunner(num_workers: int = 20, per_host_timeout: float | None = None,
              timeout: float | None = None)
```

All keyword-compatible with today's calls and with `runner.options` in the configuration
file. Each runner stores its deadlines as `run_options: RunOptions`; the core reads that
attribute (if it holds a `RunOptions`) as the runner-level options of the new entry
points.

`Nornir.arun` and `Task.arun` widen their `task` annotation to
`Callable[..., Coroutine[Any, Any, Any] | AsyncGenerator[Any, None]]` so that async
progress tasks type-check. The runtime signature is unchanged.

| Runner | `cancellation_depth` | `supports_background` | `submit` | `run_stream` | `asubmit` / `astream` |
|---|---|---|---|---|---|
| `SerialRunner` | `checkpoint` | false | `RunnerCapabilityError` | caller's thread | `RunnerNotAsyncError` |
| `ThreadedRunner` | `checkpoint` | true | background thread | background thread | `RunnerNotAsyncError` |
| `AsyncioRunner` | `immediate` | — | `RunnerNotSyncError` | `RunnerNotSyncError` | event loop |

## Processors

`Processors.task_instance_progress(task, host, partial)` calls the method on each
processor that defines it, in order. The six existing hooks are unchanged. The thread a
hook runs on:

| Hook | `ThreadedRunner` | `SerialRunner` | `AsyncioRunner` |
|---|---|---|---|
| `task_started` | caller of the entry point | caller | loop |
| `task_instance_*`, `subtask_instance_*`, `task_instance_progress` | worker running the host | caller | loop |
| `task_instance_*` for a host recorded without running | thread that recorded it (coordinator, or the caller of `cancel()`) | caller | loop, or the caller of `cancel()` |
| `task_completed` | thread driving `execute` (background thread for `submit`) | caller | loop |
