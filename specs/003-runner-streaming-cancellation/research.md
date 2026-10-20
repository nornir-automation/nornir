# Research: Runner Streaming, Cancellation, and Timeouts

**Feature**: 003-runner-streaming-cancellation | **Updated**: 2026-10-19 | [Plan](plan.md)

Research covers the current dispatch path (`nornir/core/__init__.py`, `nornir/core/task.py`,
`nornir/core/processor.py`, `nornir/plugins/runners/__init__.py`), the runner contracts in
`nornir/core/plugins/runners.py`, `load_runner` in `nornir/init_nornir.py`, and the
decisions of [spec 001](../001-asyncio-runner/spec.md). Each entry records the decision,
the reason, and the alternatives that were rejected.

## R1. One run object shared by the core and the runners

- **Decision:** Add a public `RunContext` class in a new module `nornir/core/run.py`. The
  core creates one per run and passes it to the runner. It owns every rule that must be
  identical on all runners:
  - which hosts have started, and which are recorded;
  - recording each host exactly once, in completion order;
  - the processor events for hosts the runner records without running them;
  - cancellation state and deadlines;
  - delivery of events to subscribers and the latest progress per host.

  The runner owns only concurrency: when each host starts, and how it is woken when a
  deadline passes or a cancellation arrives.
- **Rationale:** FR-001, FR-004 to FR-015 and SC-004 require the same recording rules on
  every runner. Writing them once in the core makes them testable once, and a third-party
  runner can implement the new protocol by scheduling hosts and calling `RunContext`
  methods. This keeps "concurrency stays inside the runner" (principle 7 of #1085).
- **Alternatives:** Each runner implements the handle itself: three copies of the
  recording rules, and every third-party runner would have to reproduce them exactly.
  A wrapper around `RunnerPlugin.run`: cannot cancel hosts that have not started, cannot
  enforce deadlines, and cannot deliver results in completion order.

## R2. Runner protocols: `execute` and `aexecute`

- **Decision:** Two sibling protocols in `nornir/core/plugins/runners.py`:
  - `StreamingRunner`: a `cancellation_depth` property, a `supports_background` property,
    and `execute(task, hosts, run) -> Iterator[None]`. `execute` is a generator. It runs
    until every host is recorded, and it yields whenever it wants the core to deliver
    pending events to a consumer on the same thread.
  - `AsyncStreamingRunner`: a `cancellation_depth` property and
    `async aexecute(task, hosts, run) -> None`.

  Full signatures are in [contracts/protocols.py](contracts/protocols.py).
- **Rationale:** `SerialRunner` must run tasks on the caller's thread (FR-002) and still
  deliver progress live to a `run_stream` loop on that same thread. A generator is the
  only way to interleave the runner and the consumer's loop body on one thread without a
  second thread. Runners that execute hosts on worker threads (`ThreadedRunner`) never
  need to yield, and the core drives them on a background thread.
- **Alternatives:** A blocking `execute` with callbacks: on `SerialRunner`, the consumer's
  loop body could only run after the whole run. One method per entry point (`submit`,
  `stream`): doubles the contract for every runner author.

## R3. Which thread drives `execute`

- **Decision:**

  | Entry point | `supports_background` true (`ThreadedRunner`) | false (`SerialRunner`) |
  |---|---|---|
  | `run()` | caller's thread | caller's thread |
  | `run_stream()` | background thread; the consumer reads a queue | caller's thread, interleaved with the loop body |
  | `submit()` | background thread | `RunnerCapabilityError` naming `run_stream` |

  `run()` keeps the `RunnerPlugin.run` path: `ThreadedRunner.run` and `SerialRunner.run`
  drive their own `execute` with a `RunContext` built from the runner's options, then
  return the `AggregatedResult`.
- **Rationale:** On `ThreadedRunner`, a slow loop body in the consumer must not delay
  deadline enforcement (SC-003), so the coordinator runs on its own thread. On
  `SerialRunner`, nothing leaves the caller's thread (clarification of 2026-10-19).
- **Background thread:** named `nornir-run-<id>`, not a daemon thread. The worker
  threads of `ThreadPoolExecutor` are not daemon threads either, so the process already
  waits for running hosts at exit; a daemon coordinator would only lose the final
  bookkeeping.

## R4. Cooperative cancellation: checkpoints

- **Decision:** Each host has a private state object, reachable from its task copy and
  passed on to every subtask. `task.checkpoint()` raises when that host is cancelled,
  when its own deadline has passed, or when the run deadline has passed. Without a run
  context (for example, a third-party runner using today's `run()`), `checkpoint()` does
  nothing.

  The following are also checkpoints:
  - every `yield` in a generator task: the driver checks the state before resuming the
    generator, and delivers the interruption with `generator.throw()`, so the task's
    `finally` and `except` blocks run at the `yield`;
  - the start of every subtask (`task.run()` and `task.arun()`), before
    `subtask_instance_started` fires.
- **Rationale:** FR-016 and FR-018. Making the subtask start a checkpoint gives tasks
  built from subtasks responsive cancellation without explicit calls, and it stops a
  host that was already recorded from producing more processor events.
- **FR-018:** the state stays interrupted, and each check raises a new exception
  instance.

## R5. Interruption errors and how they travel

- **Decision:** `TaskInterruptedError(BaseException)` is the base, with
  `TaskCancelledError` and `TaskTimeoutError` as subclasses, all in
  `nornir/core/exceptions.py`. Fields are listed in [contracts/errors.md](contracts/errors.md).

  Propagation:
  - A subtask that is interrupted records a failed `Result` in its own `MultiResult`,
    fires `subtask_instance_completed`, then re-raises the same interruption into the
    parent. It does **not** wrap it in `NornirSubTaskError`, which subclasses `Exception`
    and would be caught by `except Exception` (FR-017, FR-020).
  - The top-level `Task.start` and `Task.astart` catch `TaskInterruptedError` and record
    `Result(failed=True, exception=<interruption>, result=str(<interruption>))`.
  - Once a host is interrupted, its final result is the interruption, even if the task
    catches it and returns a value.
- **Rationale:** Python made the same choice for `asyncio.CancelledError` in 3.8. The
  existing `except Exception` in `Task.start` stays as it is.
- **Alternatives:** Subclassing `Exception`: rejected by FR-017. A flag that the task
  polls without an exception: tasks would have to check it after every step, and a task
  that forgets keeps running.

## R6. Recording each host exactly once

- **Decision:** `RunContext` holds one lock. Each host moves through
  `pending -> running -> recorded`, or `pending -> recorded` (never started). The first
  call that records a host wins; later attempts are dropped:
  - A worker that finishes after the runner has recorded its host as timed out returns
    without firing `task_instance_completed`, and its result is logged at debug level.
  - A subtask result that arrives after the host was recorded is not appended; the
    subtask raises the interruption instead.
  - A host's task copy is registered when the host starts, so that the runner can
    record it with the right `Task` object for the processor events.
- **Never started:** recording a host that never started fires `task_instance_started`
  and then `task_instance_completed` with a one-entry `MultiResult`, on the thread that
  records it (FR-011). `RunContext.cancel()` and the run deadline record all pending
  hosts immediately, under the lock, so a worker that dequeues one later finds it
  recorded and does not run it.
- **Final result order:** `AggregatedResult` keeps selection order, as today.
  `handle.results()` uses completion order.

## R7. Deadlines

- **Decision:**
  - The per-host deadline starts when the host starts (just before
    `task_instance_started`). The run deadline starts when the run starts (inside
    `submit`, `run_stream` or `run`, after host selection).
  - `RunOptions(per_host_timeout, timeout)` is a frozen dataclass. Values are positive
    finite numbers of seconds, or `None`. Invalid values raise `ValueError` when the
    options object or the runner is created.
  - Per-run options override the runner's options field by field: a `None` field in the
    per-run options keeps the runner's value.
  - Runners accept `per_host_timeout=None, timeout=None` as constructor keywords.
    `load_runner` already passes `config.runner.options` to the constructor, so the
    configuration file supports them with no change (FR-024).
  - All times come from `time.monotonic()`.
- **How each runner enforces deadlines:**
  - `SerialRunner`: at checkpoints, and before each host starts. A host blocked in a
    call delays the caller until the call returns (US2 scenario 6).
  - `ThreadedRunner`: the coordinator waits on a condition variable with a timeout equal
    to the next deadline, then calls `run.expire()`. `expire()` records every host past
    its deadline, and all pending hosts if the run deadline has passed. When every host
    is recorded, the coordinator calls `shutdown(wait=False, cancel_futures=True)` on the
    pool and returns, even if a worker thread is still blocked (FR-022, SC-003).
  - `AsyncioRunner`: `loop.call_at` timers call `run.expire()`, then cancel the asyncio
    tasks of the hosts it recorded. No `asyncio.timeout`, which does not exist in 3.10.
- **Alternatives:** Per-host deadline counted from `submit`: hosts waiting for a worker
  slot would time out before they start, which makes the value depend on `num_workers`.

## R8. Native cancellation on `AsyncioRunner`

- **Decision:** `run.cancel()` and `run.expire()` record the interruption reason on the
  host state first, then the runner cancels that host's asyncio task. `Task.astart`
  catches `asyncio.CancelledError` only when the host state carries a reason, and
  records the matching `TaskCancelledError` or `TaskTimeoutError` (FR-019). Without a
  reason, the `CancelledError` propagates unchanged. That is the path of
  spec 001 FR-016, where the caller cancelled the coroutine awaiting `nr.arun()` and
  nothing is recorded.
- **Swallowed cancellation:** a task that catches `CancelledError` and continues is
  interrupted again at its next checkpoint or subtask start (R4).
- **`AsyncioRunner.arun`** drives `aexecute` with a `RunContext` built from the runner's
  options, so runner deadlines apply to `nr.arun()` (FR-024). Its cancel-and-drain logic
  for an outer cancellation stays as specified in spec 001.

## R9. Generator tasks

- **Decision:**
  - Detection happens at run time, on the object the task returns:
    `inspect.isgenerator(r)` on the synchronous path, and `inspect.isasyncgen(r)` on the
    asynchronous path, before the existing `await`. A wrapper that returns the inner
    task's generator (NornFlow's `if` and `single` hooks) therefore works without
    declaring itself a generator.
  - Mode checks happen before the run, as today:
    - `_is_coroutine_task` becomes `_is_async_task` and also accepts async generator
      functions, so `nr.run()` rejects them with `AsyncTaskOnSyncRunError`.
    - `nr.arun()` rejects `def` generators with `SyncTaskOnAsyncRunError`.
  - One stepping driver, `Task._start_steps(host)`, is a generator that yields after
    each top-level `PartialResult`. `Task.start()` consumes it to the end. `SerialRunner`
    steps it from `execute` to deliver live progress on the caller's thread. Plain tasks
    pass through it unchanged: the user function is called directly, and tracebacks end
    in user code.
  - A yielded value that is not a `PartialResult` is wrapped as
    `PartialResult(host, result=value)`.
  - A yielded `Result` ends the task with that result. This is required for async
    generators, which cannot `return` a value: the `async def` example in #1086, with
    `return Result(...)` inside an async generator, is a `SyntaxError`. Found during
    implementation (2026-10-19).
  - The driver sets `partial.name` to the name of the task that yielded it, which tags
    subtask progress (FR-033).
  - Partial results go to processors that define `task_instance_progress` (checked with
    `getattr` for each processor), and to the run's subscribers. They are never stored in
    `MultiResult` (FR-032).
- **SerialRunner:** partial results from a subtask reach the stream when control next
  returns to the top-level driver (the next top-level `yield`, or the end of the host).
  Processors receive them immediately. This is listed among the documented
  `SerialRunner` differences (FR-003).
- **Behaviour change:** recorded as a bug fix in `CHANGELOG.rst` (spec Assumptions).

## R10. Streams and early exit

- **Decision:** `run_stream()` returns a `RunStream`, and `astream()` returns an
  `AsyncRunStream`. Each is single-use, provides `cancel()` and `result()`, and works as
  a context manager (`with`, `async with`). `__iter__` and `__aiter__` return a **new**
  internal iterator, never `self`. When that iterator is finalized before the stream
  has ended, it cancels the run:
  - **Sync:** the internal iterator is a generator. Its `GeneratorExit` handler calls
    `run.cancel()`. On `SerialRunner`, it then steps `execute` to the end without
    yielding, so every host is recorded before the loop's next statement.
  - **Async:** the internal iterator is a small class with `__anext__` and `__del__`.
    `__del__` calls the handle's thread-safe `cancel()`.
- **Evidence:** a probe on CPython 3.10.20, 3.12.13 and 3.14.6 showed that the loop's
  iterator is finalized before the code after the loop runs. This holds for `break`
  and for an exception raised in the loop body, even while the exception's traceback is
  kept alive, for both `for` and `async for`. Returning `self` from `__iter__` would
  break this, because the variable holding the stream keeps it alive.
- **Guarantee:** `with`, `async with` and explicit `cancel()` cancel the run on every
  interpreter. Plain-loop cancellation relies on CPython reference counting, which is
  the only interpreter in the support matrix. The guide states both.
- **Subscription race:** `run_stream` subscribes before the first host starts, so no
  event is lost. `handle.events()` subscribes when called (FR-007).
- **Alternatives:** An async generator for `astream`: it is closed by the event loop's
  finalizer hook at an unspecified later time, which is not immediate. A mandatory
  `with` block: changes the API shown in the issue.

## R11. Handles

- **Decision:**
  - `RunHandle` (thread-based) and `AsyncRunHandle` (event-loop based) have the same
    members, apart from the async iterators and the awaited `result()`. They are listed
    in [contracts/entry-points.md](contracts/entry-points.md).
  - `results()` replays a list of final `Result` objects in completion order, then waits
    on a `threading.Condition` (sync) or an `asyncio.Event` (async).
  - `events()` gives each subscriber its own unbounded queue: `queue.SimpleQueue` or
    `asyncio.Queue`.
  - `progress()` returns a copy of the latest-partial map (FR-023).
  - `cancel()` on `AsyncRunHandle` from another thread is forwarded with
    `loop.call_soon_threadsafe`.
  - `result()` on `AsyncRunHandle` awaits a shielded future, so cancelling the waiter
    does not cancel the run (FR-014).
  - The handle keeps a strong reference to its asyncio task.
  - `id` is `uuid.uuid4().hex`.
- **Memory:** a consumer that stops reading `events()` without leaving the loop keeps
  its queue growing. The guide documents this; the handle itself keeps only the latest
  partial result per host.
- **Internal failure:** if the runner raises (a bug, not a task failure), the run is
  marked done, iterators end, and `result()` re-raises that error.

## R12. Lifecycle and `raise_on_error`

- **Decision:** `_finalize_run` is split into two steps: update `failed_hosts` or decide
  to raise, then fire `task_completed`. The order of today's `run()` is kept exactly:
  - When `raise_on_error` applies and a host failed, `run()` raises before
    `task_completed`, so processors never receive `task_completed` for that run.
  - A background run reproduces this: it skips `task_completed` and raises
    `NornirExecutionError` from every call of `handle.result()` (FR-026, FR-028).
- **Thread:** finalization runs on the thread that drives `execute`: the background
  coordinator for `submit`, and the caller for `run()` and a `SerialRunner` stream.
  `nr.data.failed_hosts` is a set updated in one call, as today.
- **Validation before events:** `submit`, `run_stream`, `asubmit` and `astream` check
  task mode, runner mode and runner capability before `_prepare_run`, so a rejected call
  fires no processor event.

## R13. Interruption on the caller's thread during `run()`

- **Decision:** keep today's behaviour. If `KeyboardInterrupt` (or another
  `BaseException`) reaches the thread driving `run()` on `ThreadedRunner` or
  `SerialRunner`, the driver shuts the pool down with `wait=False` and without
  `cancel_futures`, records nothing, does not finalize, and propagates the exception.
  Queued hosts still run in the worker threads, as they do today.
- **Rationale:** the non-goals of #1086 exclude any change to the existing synchronous
  path. A caller who wants queued hosts to stop on Ctrl-C uses `submit` or
  `run_stream` and calls `cancel()`, or leaves the loop.
- **Alternative rejected (2026-10-19):** calling `run.cancel()` on the way out, so that
  queued hosts never start. It is a better experience, but it is a change to `run()`
  that the spec does not approve.
