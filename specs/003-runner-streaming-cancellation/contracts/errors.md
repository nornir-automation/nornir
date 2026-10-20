# Contract: Errors

**Feature**: 003-runner-streaming-cancellation | [Plan](../plan.md)

All in `nornir/core/exceptions.py`.

## Interruptions (`BaseException`)

```text
BaseException
└── TaskInterruptedError
    ├── TaskCancelledError
    └── TaskTimeoutError
```

| Class | Fields | Message example |
|---|---|---|
| `TaskInterruptedError` | `host_name: str`, `task_name: str`, `started: bool` (positional, default `True`); `fresh()` returns a new instance with the same fields | — (base, not raised directly) |
| `TaskCancelledError` | inherited | `Task 'upgrade' on host 'rtr-1' was cancelled.` / `... was cancelled before it started.` |
| `TaskTimeoutError` | `(host_name, task_name, timeout, scope, started=True)`, with `timeout: float` and `scope: Literal["host", "run"]` | `Task 'upgrade' on host 'rtr-1' exceeded its per-host timeout of 600 seconds.` / `... exceeded the run timeout of 3600 seconds.` / `... did not start before the run timeout of 3600 seconds.` |

- Subclasses `BaseException` so that `except Exception` does not catch them (FR-017).
- Carried by `Result(failed=True, exception=...)`, with `result` set to the message.
- Fields are plain strings, booleans and numbers, and the classes define `__reduce__`, so
  instances pickle (`tests/core/test_run_errors.py`) and can be serialised by a later
  out-of-process runner.
- `started=False` marks a host that never started (FR-010).

## `RunnerCapabilityError(Exception)`

| Field | Meaning |
|---|---|
| `runner_name: str` | Class name of the runner |
| `capability: str` | One of `submit`, `run_stream`, `asubmit`, `astream` |
| `background: bool` | `True` when the runner streams but does not support background runs (default `False`) |

Messages:

- Third-party runner without the protocol:
  `MyRunner does not support 'run_stream'. Implement StreamingRunner, or use run().`
  For `asubmit` and `astream`: `... Implement AsyncStreamingRunner, or use arun().`
- `SerialRunner` with `submit`:
  `SerialRunner does not support background runs ('submit') because it runs every task on
  the caller's thread. Use 'run_stream' to consume the run live, or use ThreadedRunner.`

Not a subclass of `SyncAsyncMismatchError`: it is about a missing capability, not about
mixing modes.

## Unchanged errors reused

`AsyncTaskOnSyncRunError`, `SyncTaskOnAsyncRunError`, `RunnerNotSyncError`,
`RunnerNotAsyncError` (spec 001) and `NornirExecutionError` keep their classes and
messages. `AsyncTaskOnSyncRunError` now also covers async generator functions passed to
`run()`, `submit()` or `run_stream()`.
