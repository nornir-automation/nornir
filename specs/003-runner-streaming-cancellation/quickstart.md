# Quickstart: Validating Runner Streaming, Cancellation, and Timeouts

**Feature**: 003-runner-streaming-cancellation | [Plan](plan.md) | [Entry points](contracts/entry-points.md)

## Prerequisites

```bash
uv sync --locked
make pytest          # fast loop while implementing
make tests           # all five gates before review
```

No device is needed. Every scenario uses the test inventory under `tests/inventory_data`
and tasks that sleep, wait on an event, or yield, in place of device I/O. Tasks that
block "forever" wait on a `threading.Event` that the test sets during teardown, so that
no worker thread outlives the test session.

## Scenarios

Each scenario names the requirement or criterion it proves. Expected outcomes are the
pass conditions.

### 1. Abort on first failure (US1, SC-001, SC-004)

```python
run = nr.submit(task=step_task)        # one host fails at once; others checkpoint each second
for res in run.results():
    if res.failed:
        run.cancel()
        break
result = run.result()
```

Expected, on `ThreadedRunner` and on `AsyncioRunner` (with `asubmit`):

- one entry per host;
- no host started after `cancel()`;
- the run finishes within 2 seconds of `cancel()`, on a 100-host run;
- cancelled hosts carry `TaskCancelledError`, and those that never started have
  `started=False`;
- with `raise_on_error` off, cancelled hosts are in `nr.data.failed_hosts`.

### 2. Same code on `SerialRunner` and `ThreadedRunner` (FR-001, US1 scenario 8)

Run the same `run_stream` loop, which breaks on the first failed result, with each runner.
Expected: identical sets of recorded hosts and error types. On `SerialRunner`, every task
runs on the main thread (`threading.current_thread()` is the main thread), and
`nr.submit()` raises `RunnerCapabilityError` naming `run_stream`.

### 3. Run deadline with a blocked host (US2, SC-003, FR-022)

`ThreadedRunner(timeout=2)`, one host blocked on an event that is never set. Expected:
`nr.run()` returns within 3 seconds; the blocked host and every host not started carry
`TaskTimeoutError`; other hosts keep their own results.

### 4. Immediate cancellation on asyncio (SC-002, FR-019)

`AsyncioRunner(per_host_timeout=0.5)`, a task awaiting `asyncio.sleep(3600)` with no
checkpoint. Expected: the host is recorded with `TaskTimeoutError` within 0.6 seconds.
Cancelling the coroutine that awaits `nr.arun()` instead still records nothing (spec 001
FR-016).

### 5. `except Exception` does not stop a cancellation (US1 scenario 5, FR-017, FR-018)

A task wraps subtask calls in `try/except Exception: continue`. Expected: after
`cancel()`, the host is recorded as cancelled at its next subtask start; a task that
catches `TaskCancelledError` explicitly is interrupted again at its next checkpoint.

### 6. Progress (US3)

A generator task yields "uploading" and "rebooting", then returns a `Result`. Expected:

- `run_stream` delivers two `PartialResult` events and one final `Result` per host;
- a processor defining `task_instance_progress` receives both partial results under
  plain `nr.run()`;
- a processor without the method is never called with them;
- every host's `MultiResult` contains only `Result` objects;
- on `SerialRunner`, the first partial result reaches the loop before the host
  finishes.

### 7. Early exit cancels (FR-009, research R10)

Leave a `run_stream` loop with `break`, and in another test by raising inside the loop
body while keeping the exception object alive. Expected: the run is cancelled before the
statement after the loop. Leaving a loop over `handle.results()` does not cancel.

### 8. Existing behaviour (SC-005)

Run the unchanged test suite and `make nbval`. Add a runner and a processor written
against today's protocols only (a test fixture). Expected: `run()` works with both;
`submit` on that runner raises `RunnerCapabilityError`.

### 9. Matrix (SC-006)

The timing tests of scenarios 1, 3 and 4 run in the CI matrix: Linux, macOS, Windows,
Python 3.10 to 3.14. Margins are those of the success criteria; no test tightens them.

## Documentation checks

- New executed notebook `docs/howto/long_running_tasks.ipynb` covering scenarios 1, 3
  and 6, with genuine output (`make nbval`).
- `docs/plugins/execution_model.rst` lists the cancellation depth of each runner and the
  `SerialRunner` differences (FR-003); the processor thread table of
  [entry-points.md](contracts/entry-points.md) (FR-029).
- `CHANGELOG.rst` entry under 3.7.0, including the generator-task fix.
- `make docs` regenerates `docs/api/nornir/core/run.rst`; commit it.
