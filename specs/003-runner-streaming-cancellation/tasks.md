---

description: "Task list for runner streaming, cancellation, and timeouts"
---

# Tasks: Runner Streaming, Cancellation, and Timeouts

**Input**: Design documents from `specs/003-runner-streaming-cancellation/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required. Constitution principle IV requires tests with every behavioural
change. In each story phase, the test tasks come first and must fail before the
implementation tasks of that phase.

## Format and conventions

- Each task has a checkbox, a sequential ID, an optional [P], a story label in story
  phases, and exact repository-relative paths.
- [P] means the task touches files that no other open task in the same phase writes, and
  its stated prerequisites are done. It never allows two tasks to write one file at the
  same time.
- Research decisions are cited as R1–R13 ([research.md](research.md)). Exact signatures
  are in [contracts/protocols.py](contracts/protocols.py); entry-point rules in
  [contracts/entry-points.md](contracts/entry-points.md); errors in
  [contracts/errors.md](contracts/errors.md).
- Existing tests must pass unchanged (SC-005). No existing test file is edited.
- No new dependency, no `# type: ignore`, no new entry in the ruff ignore list.
- Tasks that block "forever" in tests wait on a `threading.Event` (or `asyncio.Event`)
  that a fixture sets at teardown, so no worker thread outlives the test.
- Evidence (commands and their output) goes in
  `specs/003-runner-streaming-cancellation/validation.md`. A gate task is not checked
  without real output. Commit or push only when asked.

## Phase 1: Setup

**Purpose**: Record the starting state and add shared test helpers.

- [X] T001 Run `uv sync --locked`, `make pytest`, and `make mypy` from `Makefile`, and
  record the commands, the pass counts, and any existing failure in a new file
  `specs/003-runner-streaming-cancellation/validation.md`.
- [X] T002 [P] Create `tests/core/run_helpers.py` with shared helpers, typed for strict
  mypy:
  - `make_nornir(runner, num_hosts, processors=())` builds a `Nornir` with `num_hosts`
    plain `Host` objects (`h000`, `h001`, …), reusing the inventory classes from
    `nornir.core.inventory` as `tests/conftest.py` does;
  - `EventLog`, a processor that records `(hook, task_name, host_name, thread_name)` for
    the six existing hooks and for `task_instance_progress`, behind a lock;
  - `steps_task(task, steps, interval)`, which calls `task.checkpoint()` then sleeps
    `interval` seconds, `steps` times;
  - `fail_now_task(task)`, which raises `ValueError`;
  - `blocked_task(task, release)`, which waits on the `threading.Event` it is given;
  - async counterparts `asteps_task`, `ablocked_task`.

  Add a `release` fixture to the existing `tests/core/conftest.py`: it returns a
  `threading.Event` and sets it at teardown, so no blocked worker thread outlives the
  test. pytest only discovers fixtures in `conftest.py` and test modules, so the
  fixture cannot live in `run_helpers.py`.

---

## Phase 2: Foundational

**Purpose**: The run state, the interruption errors, the runner protocols, and the
re-wiring of `run()` / `arun()` onto `execute` / `aexecute`. Every story depends on this
phase. At the end, the existing suite still passes unchanged.

### Tests (write first, expect failures)

- [X] T003 [P] Create `tests/core/test_run_errors.py`:
  - `TaskInterruptedError` subclasses `BaseException` and not `Exception`;
  - `TaskCancelledError` and `TaskTimeoutError` subclass it;
  - fields and messages match `contracts/errors.md`, including the never-started forms
    and `scope="run"`;
  - pickling round-trips every class with its fields;
  - `RunnerCapabilityError` subclasses `Exception` and not `SyncAsyncMismatchError`, and
    both message forms match.
- [X] T004 [P] Create `tests/core/test_run_context.py`, using a `RunContext` built
  directly with a `Task`, three hosts and `RunOptions()`:
  - `start_host` records a host once; a second record of the same host is dropped and
    fires no processor event (R6);
  - `cancel()` records every pending host with `TaskCancelledError(started=False)`, and
    `EventLog` shows `task_instance_started` then `task_instance_completed` for each
    (FR-010, FR-011); `start_host` on such a host returns the record without calling
    the task;
  - `cancel()` is idempotent and calls each cancel callback once; a callback added after
    cancellation is called at once;
  - a running task that calls `task.checkpoint()` after `cancel()` is recorded with
    `TaskCancelledError(started=True)`; a task that catches it and calls
    `checkpoint()` again gets a new exception (FR-018);
  - a task with `try: task.run(sub) except Exception: pass` around a cancelled subtask
    is still recorded as cancelled (FR-017, FR-020); the subtask's own `MultiResult`
    holds a failed `Result` and `subtask_instance_completed` fired;
  - starting a subtask after `cancel()` raises before `subtask_instance_started`
    fires (R4);
  - `task.checkpoint()` outside any run context does nothing;
  - `finished` becomes true when every host is recorded, and `wait_for_change` returns
    when a host is recorded.
- [X] T005 [P] Create `tests/core/test_run_contract.py`:
  - the existing `SerialRunner`, `ThreadedRunner`, `AsyncioRunner` are assigned to
    variables typed `StreamingRunner` / `AsyncStreamingRunner` (checked by `make mypy`)
    and report the depth and background values of the runner table in
    `contracts/entry-points.md`;
  - a test-only `LegacyRunner` implementing only `RunnerPlugin.run`, and a processor
    implementing only the six existing hooks, still work with `nr.run()` (SC-005).

### Implementation

- [X] T006 [P] Add `TaskInterruptedError`, `TaskCancelledError`, `TaskTimeoutError`, and
  `RunnerCapabilityError` to `nornir/core/exceptions.py` per `contracts/errors.md`,
  with `__reduce__` so they pickle with their fields (R5).
- [X] T007 [P] Add `CancellationDepth`, `StreamingRunner`, and `AsyncStreamingRunner` to
  `nornir/core/plugins/runners.py` per `contracts/protocols.py`. Leave `RunnerPlugin`,
  `AsyncRunnerPlugin`, and `RunnersPluginRegister` unchanged. Use a `TYPE_CHECKING`
  import for `RunContext` to avoid an import cycle (plan "Structure decision").
- [X] T008 [P] Add `PartialResult` to `nornir/core/task.py` per
  `contracts/protocols.py`, raising `ValueError` for a `progress` outside 0–1 (data
  model). Do not change `Result`, `MultiResult`, or `AggregatedResult`.
- [X] T009 [P] Add the `ProgressProcessor` protocol and
  `Processors.task_instance_progress(task, host, partial)` to `nornir/core/processor.py`.
  The method calls the hook only on processors that define it, found with `getattr`.
  Leave `Processor` and the six existing `Processors` methods unchanged.
- [X] T010 Create `nornir/core/run.py` with `RunOptions` (frozen dataclass, validation
  per R7) and `RunContext` per data-model.md: per-host state under one lock and
  condition, `start_host`, `astart_host`, `step_host` (delegating to the task),
  record-once, never-started recording with its two events, `cancel`,
  `add_cancel_callback`, `wait_for_change`, `finished`, `options`, `cancelled`, the
  completion-order list, and private `_subscribe` / `_unsubscribe` for event
  subscribers. Leave `expire` and `next_deadline` returning "nothing due" until T028.
  After T006 and T008.
- [X] T011 Update `Task` in `nornir/core/task.py` (after T010):
  - add a private host-state reference, set by `RunContext` and passed to subtasks in
    `_create_subtask`;
  - add `checkpoint()` (R4);
  - make the subtask start a checkpoint before `subtask_instance_started`;
  - add the private stepping driver `_start_steps(host)` and make `start()` consume it,
    without generator support yet (R9);
  - in the top-level `start()` / `astart()`, catch `TaskInterruptedError` and record it
    (R5);
  - in a subtask, record the interruption, fire `subtask_instance_completed`, then
    re-raise it;
  - in `astart()`, convert `asyncio.CancelledError` only when the host state carries a
    reason (R8);
  - in `_finish` / `_record_subtask_result`, drop results for a host that is already
    recorded (R6).

  Keep the signatures of `start`, `astart`, `run`, `arun`, and `copy`.
- [X] T012 Implement `execute` on `SerialRunner` and `ThreadedRunner` and `aexecute` on
  `AsyncioRunner` in `nornir/plugins/runners/__init__.py`, with the
  `cancellation_depth` / `supports_background` attributes from the runner table:
  - `SerialRunner.execute`: `yield from run.step_host(task.copy(), host)` for each host;
  - `ThreadedRunner.execute`: a pool created without the context manager, one
    `run.start_host` submission per host, and a coordinator loop on
    `run.wait_for_change` until `run.finished`, then
    `shutdown(wait=False, cancel_futures=True)`;
  - `AsyncioRunner.aexecute`: the spec 001 semaphore with `run.astart_host`.

  Re-implement each runner's `run()` / `arun()` to build a `RunContext` with
  `RunOptions()`, drive `execute` / `aexecute`, and return the `AggregatedResult` in
  selection order. Keep `AsyncioRunner.run` raising `RunnerNotSyncError`, and keep the
  outer-cancellation drain of spec 001 in `arun`. On a `BaseException` reaching the
  thread that drives `run()`, keep today's behaviour per R13: shut the pool down with
  `wait=False` and without `cancel_futures`, record nothing, and propagate. After T007
  and T011.
- [X] T013 Split `Nornir._finalize_run` in `nornir/core/__init__.py` into a step that
  updates `failed_hosts` or returns the `NornirExecutionError` to raise, and a step
  that fires `task_completed`. `run()` and `arun()` must keep today's exact order,
  including no `task_completed` when raising (R12).
- [X] T014 Gate: run `make pytest`, `make mypy`, and `make ruff`. T003–T005 pass, and every
  pre-existing test passes unchanged (SC-005). Record the output in
  `specs/003-runner-streaming-cancellation/validation.md`.

**Checkpoint**: run state, errors and protocols exist; `run()` / `arun()` behave as
before.

---

## Phase 3: User Story 1 — Abort the remaining hosts after a failure (Priority: P1)

**Goal**: start a run in the background, read each host's final result as it finishes,
cancel on the first failure, and get every host accounted for, on `ThreadedRunner` and
`AsyncioRunner`; the same `run_stream` code also works on `SerialRunner`.

**Independent test**: [quickstart.md](quickstart.md) scenarios 1, 2, 5 and 7.

### Tests (write first, expect failures)

- [X] T015 [P] [US1] Create `tests/core/test_run_handle.py` for `ThreadedRunner` and
  `nr.submit`:
  - US1 scenario 1 on 20 hosts: one `fail_now_task` host and 19 `steps_task` hosts;
  - scenario 2: `failed_hosts` is updated without calling `result()` (FR-012);
  - scenario 3: the `EventLog` order, with `task_started` logged before `submit`
    returns (FR-011, FR-026);
  - scenario 4: `raise_on_error` (FR-028);
  - scenario 6: two threads iterating `results()` plus a double `cancel()` (FR-006,
    FR-015);
  - `results()` called after some hosts finished replays them first;
  - hosts are selected at `submit` time (FR-027);
  - `cancel()` before any host starts records every host as never started;
  - after `cancel()`, a `blocked_task` host with no deadline is not recorded while it
    is blocked (`result(timeout=0.5)` raises `TimeoutError`), and it is recorded as
    cancelled once the `release` event lets it reach its next checkpoint;
  - zero selected hosts gives a handle that is already done, with an empty result;
  - `result(timeout=0.01)` raises `TimeoutError` while the run is in progress;
  - `id` is unique per run;
  - SC-001: 100 hosts with one checkpoint per second finish within 2 s of `cancel()`.
- [X] T016 [P] [US1] Create `tests/core/test_async_run_handle.py` for `AsyncioRunner`
  and `await nr.asubmit`:
  - the async equivalents of T015;
  - `cancel()` called from another thread (FR-015);
  - cancelling a coroutine that awaits `handle.result()` leaves the run going (FR-014);
  - cancelling the coroutine that awaits `nr.arun()` still records nothing, with no
    `task_completed` (US1 scenario 7);
  - a host awaiting `asyncio.sleep(3600)` without a checkpoint is recorded as
    cancelled within 0.1 s of `cancel()` (FR-019).
- [X] T017 [P] [US1] Create `tests/core/test_run_stream.py`:
  - US1 scenario 8: the same `run_stream` loop, which breaks on the first failed
    result, run on `SerialRunner` and on `ThreadedRunner`, giving the same recorded
    hosts and error types; on `SerialRunner`, every task runs on the main thread
    (FR-001, FR-002);
  - scenario 9: `nr.submit` on `SerialRunner` raises `RunnerCapabilityError` naming
    `run_stream` (FR-003);
  - an exception raised inside the loop body, with the exception object kept alive,
    cancels the run before the next statement (R10);
  - a `with` block cancels on exit;
  - leaving a `handle.results()` loop early does not cancel (FR-009);
  - a second iteration raises `RuntimeError`;
  - `stream.result()` works after the loop on both runners;
  - `astream` with `break` cancels the run.
- [X] T018 [P] [US1] Extend `tests/core/test_run_contract.py` with the check rows of
  `contracts/entry-points.md`:
  - `submit` / `run_stream` with an async task → `AsyncTaskOnSyncRunError`;
  - `asubmit` with a `def` task → `SyncTaskOnAsyncRunError`;
  - `submit` on `AsyncioRunner` → `RunnerNotSyncError`;
  - `asubmit` on `ThreadedRunner` → `RunnerNotAsyncError`;
  - `submit` / `run_stream` on `LegacyRunner` → `RunnerCapabilityError` (FR-035).

  In every rejected case, `EventLog` must be empty.

### Implementation

- [X] T019 [US1] Add `RunHandle` and `AsyncRunHandle` to `nornir/core/run.py` per
  `contracts/protocols.py` and R11:
  - `results()` replays the completion-order list, then waits on the condition
    (sync) or an `asyncio.Event` (async);
  - `events()` uses a subscriber queue (`queue.SimpleQueue` / `asyncio.Queue`);
  - `progress()` returns a copy;
  - `cancel()` on `AsyncRunHandle` uses `loop.call_soon_threadsafe` when called off the
    loop thread;
  - `result()` re-raises the stored `NornirExecutionError` or internal error; the async
    version awaits a shielded future;
  - `id` is `uuid4().hex`.
- [X] T020 [US1] Add `RunStream` and `AsyncRunStream` to `nornir/core/run.py` per R10:
  - `__iter__` returns a new generator whose `GeneratorExit` handler cancels the run,
    and on a non-background runner steps `execute` to the end without yielding;
  - `__aiter__` returns a new iterator object whose `__del__` cancels the run;
  - `with` / `async with` support;
  - single use, enforced with `RuntimeError`;
  - `result()`.

  On a background runner, subscribe before the first host starts.
- [X] T021 [US1] Add `Nornir.submit` and `Nornir.run_stream` to `nornir/core/__init__.py`
  with the signatures of `contracts/entry-points.md`, including the `run_options`
  parameter:
  - run the checks of the entry-point table before `_prepare_run`;
  - for `submit`, start a non-daemon thread `nornir-run-<id>` that drives `execute`,
    then finalizes with the T013 steps without raising;
  - for `run_stream` on a non-background runner, drive `execute` on the caller's
    thread (R3).

  Put the shared check helpers in private functions next to `_is_async_runner`.
- [X] T022 [US1] Add `Nornir.asubmit` and `Nornir.astream` to `nornir/core/__init__.py`:
  run the checks, call `_prepare_run`, create an asyncio task on the running loop that
  awaits `aexecute` then finalizes, and keep a strong reference to it in the handle.
- [X] T023 [US1] Wire cancellation into the runners in `nornir/plugins/runners/__init__.py`:
  - `ThreadedRunner` registers a cancel callback that wakes the coordinator and
    cancels queued futures;
  - `AsyncioRunner` registers a callback that, through `call_soon_threadsafe`, cancels
    the asyncio tasks of hosts in the running state after `RunContext` has stored the
    reason (R8);
  - `SerialRunner` relies on checkpoints and on `RunContext` recording pending hosts.
- [X] T024 [US1] Gate: run `make pytest`, `make mypy`, and `make ruff`. T015–T018 pass,
  and so do T003–T005 and the existing suite. Record the output in
  `specs/003-runner-streaming-cancellation/validation.md`.

**Checkpoint**: P1 is usable on its own: fail-fast across hosts on all three runners.

---

## Phase 4: User Story 2 — Deadlines per host and per run (Priority: P2)

**Goal**: `per_host_timeout` and `timeout` on the runner or per run; a stuck host no
longer blocks the run.

**Independent test**: [quickstart.md](quickstart.md) scenarios 3 and 4.

### Tests (write first, expect failures)

- [X] T025 [P] [US2] Create `tests/core/test_run_deadlines.py`:
  - US2 scenario 1 / SC-003: `ThreadedRunner(timeout=2)` with one `blocked_task` host;
    `nr.run()` returns within 3 s, and the blocked host and the hosts that never
    started carry `TaskTimeoutError` (`scope="run"` for the latter) (FR-022);
  - scenario 2: per-run `RunOptions(per_host_timeout=0.2)` overrides
    `ThreadedRunner(per_host_timeout=600)`, and a `None` field keeps the runner value
    (FR-025);
  - scenario 3: plain `nr.run()` applies a runner `per_host_timeout` (FR-024);
  - scenario 4: `nr.run(task, timeout=30)` passes `timeout` to a task parameter of that
    name (FR-023);
  - scenario 6: `SerialRunner(per_host_timeout=0.2)` records the host at its next
    checkpoint and starts the next host;
  - with `ThreadedRunner(num_workers=1, per_host_timeout=0.5)`, the per-host clock
    starts when a host starts, not at `submit`;
  - `RunOptions` and runner constructors reject 0, negative, `inf`, `nan`, and `True`
    with `ValueError`;
  - `InitNornir(runner={"plugin": "threaded", "options": {"per_host_timeout": 1}})`
    passes the value to the runner;
  - a worker finishing after its host was recorded as timed out fires no further
    processor event.
- [X] T026 [P] [US2] Create `tests/core/test_async_run_deadlines.py`:
  - US2 scenario 5 / SC-002: `AsyncioRunner(per_host_timeout=0.5)` with
    `ablocked_task` is recorded with `TaskTimeoutError` within 0.6 s, with no
    checkpoint in the task;
  - a run `timeout` records hosts waiting on the semaphore as never started;
  - `nr.arun()` applies runner deadlines (FR-024);
  - a task that catches `asyncio.CancelledError` and continues is interrupted at its
    next checkpoint.

### Implementation

- [X] T027 [US2] Add `per_host_timeout=None, timeout=None` keyword parameters to the
  three runner constructors in `nornir/plugins/runners/__init__.py`, validated as in
  R7, and use them as the runner-level `RunOptions` in `run()` / `arun()`. Add the
  private merge function (per-run field over runner field) in `nornir/core/run.py`, and
  apply it in `Nornir.submit`, `run_stream`, `asubmit`, and `astream` in
  `nornir/core/__init__.py`.
- [X] T028 [US2] Implement the deadlines in `RunContext` in `nornir/core/run.py` (R7,
  data model):
  - set the run deadline at start and each host deadline at host start;
  - `expire()` records running hosts past their deadline and, after the run deadline,
    every pending host;
  - `next_deadline()`;
  - make `checkpoint()` in `nornir/core/task.py` raise `TaskTimeoutError` when a
    deadline has passed.
- [X] T029 [US2] Use the deadlines in the runners in `nornir/plugins/runners/__init__.py`:
  - `ThreadedRunner`: the coordinator waits up to `next_deadline()`, calls `expire()`,
    and returns as soon as `run.finished`, without waiting for blocked workers;
  - `AsyncioRunner`: `loop.call_at` timers call `expire()` and cancel the asyncio
    tasks of the hosts it returns; timers are cleared when the run ends;
  - `SerialRunner`: checks the run deadline before each host.
- [X] T030 [US2] Gate: run `make pytest`, `make mypy`, and `make ruff`. T025–T026 pass,
  and so does every earlier test. Record the output in
  `specs/003-runner-streaming-cancellation/validation.md`.

**Checkpoint**: deadlines work on all runners and entry points, including plain
`run()`.

---

## Phase 5: User Story 3 — Progress from long tasks (Priority: P3)

**Goal**: generator tasks report `PartialResult` objects to streams, handles, and
processors, without changing `MultiResult`.

**Independent test**: [quickstart.md](quickstart.md) scenario 6.

### Tests (write first, expect failures)

- [X] T031 [P] [US3] Create `tests/core/test_run_progress.py`:
  - US3 scenario 1: `run_stream` delivers two `PartialResult` events and one final
    `Result` per host, on `SerialRunner` and on `ThreadedRunner`;
  - scenario 2: `EventLog` receives both partial results under plain `nr.run()`, and
    every `MultiResult` holds only `Result` objects (FR-013, FR-032);
  - scenario 3: a processor without `task_instance_progress` is never called with
    partial results (FR-031);
  - scenario 5: a late `events()` subscriber receives only new events, and
    `progress()` returns the latest partial result per host (FR-007, FR-008);
  - scenario 6: a subtask's partial results carry the subtask name, and `task.run()`
    still returns its `MultiResult` (FR-033);
  - scenario 7: an async generator function passed to `run()` / `submit()` raises
    `AsyncTaskOnSyncRunError` (FR-030);
  - a plain `def` wrapper that returns a generator task's generator runs it as a
    progress task (R9);
  - a yielded non-`PartialResult` value is wrapped;
  - a generator with no `return` gives `Result(result=None)`;
  - a `yield` is a checkpoint: after `cancel()`, the interruption is thrown at the
    `yield`, the generator's `finally` runs, and a generator that catches it and
    yields again is interrupted again;
  - on `SerialRunner`, the first partial result reaches the loop before the host
    finishes;
  - regression for the bug fix: a generator task's body runs, and its generator object
    is never stored as `Result.result`.
- [X] T032 [P] [US3] Create `tests/core/test_async_run_progress.py`: async generator
  tasks on `AsyncioRunner` through `astream`, `asubmit().events()` and `nr.arun()`; a
  `def` generator passed to `arun()` / `asubmit()` raises `SyncTaskOnAsyncRunError`;
  cancellation interrupts an async generator at its current `await`.

### Implementation

- [X] T033 [US3] In `nornir/core/task.py`, rename `_is_coroutine_task` to
  `_is_async_task` so that it also returns true for async generator functions
  (unwrapping `functools.partial` and checking `__call__`, as today). Update every
  caller in `nornir/core/task.py` and `nornir/core/__init__.py`. The function is
  private, so no alias is needed.
- [X] T034 [US3] Add generator support to the drivers in `nornir/core/task.py` (R9):
  - in `_start_steps`, when the task returns a generator (`inspect.isgenerator`), check
    the host state before each resume and deliver an interruption with `throw()`;
  - wrap yielded values that are not `PartialResult`, set `partial.name` to the
    yielding task's name, call `processors.task_instance_progress`, publish to the
    host state, and yield to the stepping caller only for top-level tasks;
  - take the `StopIteration` value as the task result;
  - in `astart`, drive an async generator (`inspect.isasyncgen`) with `__anext__` and
    `athrow` in the same way.
- [X] T035 [US3] In `nornir/core/run.py`, publish partial results from the host state:
  - update the latest-partial map;
  - deliver to subscribers;
  - make `step_host` yield after each top-level partial result, and flush buffered
    subtask partial results to the stream at the next top-level yield or at host end
    (R9, "SerialRunner").
- [X] T036 [US3] Gate: run `make pytest`, `make mypy`, and `make ruff`. T031–T032 pass,
  and so does every earlier test. Record the output in
  `specs/003-runner-streaming-cancellation/validation.md`.

**Checkpoint**: all three stories work together.

---

## Phase 6: Polish and cross-cutting concerns

- [X] T037 [P] Create `docs/howto/long_running_tasks.ipynb` covering quickstart
  scenarios 1, 3 and 6 on the test inventory, execute it, and commit its real output.
  Add any output that varies between runs (run ids, timings) to
  `docs/nbval_sanitize.cfg`. Link the notebook from `docs/howto/index.rst`.
- [X] T038 [P] Update `docs/plugins/execution_model.rst`:
  - the runner table (cancellation depth, background support, entry points) from
    `contracts/entry-points.md`;
  - the `SerialRunner` differences (FR-003): no `submit`; a blocked host delays the
    caller; subtask progress reaches the stream at the next top-level `yield`;
    cancellation by leaving the loop;
  - the processor-thread table (FR-029);
  - the limits of cancellation on threads (checkpoints, blocked calls keep their worker
    slot);
  - `with` / `async with` for guaranteed cancellation on early exit (R10);
  - a section for runner authors on implementing `StreamingRunner` /
    `AsyncStreamingRunner` with `RunContext`.
- [X] T039 [P] Add a `CHANGELOG.rst` entry under 3.7.0 for #1086. It covers the new
  entry points, cancellation, deadlines and progress, plus the generator-task bug fix:
  tasks containing `yield` now run instead of reporting success without running (spec
  Assumptions).
- [X] T040 Run `make docs`, then commit the regenerated `docs/api/nornir/core/run.rst`
  and any other files under `docs/api/nornir/` that it rewrites. Do not edit them by
  hand. After T037–T039.
- [X] T041 Run quickstart scenarios 1–8 from
  `specs/003-runner-streaming-cancellation/quickstart.md` and record the results in
  `specs/003-runner-streaming-cancellation/validation.md`. Scenario 9 (the CI matrix)
  is recorded as pending until CI runs.
- [X] T042 Gate: run `make tests` (ruff, mypy, nbval, pytest, docs), and record the full
  output in `specs/003-runner-streaming-cancellation/validation.md`.
- [X] T043 If any name or signature changed during implementation, update
  `specs/003-runner-streaming-cancellation/contracts/protocols.py`,
  `contracts/entry-points.md`, `contracts/errors.md` and `data-model.md` to match, and
  re-run `make ruff` and `make mypy`.

---

## Dependencies and execution order

```text
Phase 1 (T001–T002)
  └─ Phase 2 Foundational (T003–T014)      blocks all stories
       ├─ Phase 3 US1 (T015–T024)          P1
       │    └─ Phase 4 US2 (T025–T030)     reuses US1 cancellation recording and entry points
       └─ Phase 5 US3 (T031–T036)          needs Phase 2; its stream tests also need T019–T022
            └─ Phase 6 Polish (T037–T043)  after every story
```

- Within Phase 2: T003–T005 first. Then T006, T007, T008 and T009 in parallel. Then
  T010, T011, T012 and T013 in order, then T014.
- US2 depends on US1 for `submit`, `run_stream` and the handle, which it extends with
  `run_options`.
- US3 depends on Phase 2 for the driver and on US1 for streams and handles. Its
  generator work (T033–T034) can start right after Phase 2.

## Parallel opportunities

- **Phase 2:**
  - tests T003, T004 and T005 (three new files);
  - then T006 (`exceptions.py`), T007 (`plugins/runners.py`), T008 (`task.py`) and
    T009 (`processor.py`).
- **US1:** tests T015, T016, T017 and T018 in parallel. Implementation is sequential,
  because T019–T020 share `run.py` and T021–T022 share `core/__init__.py`.
- **US2:** tests T025 and T026 in parallel.
- **US3:** tests T031 and T032 in parallel. T033–T034 (`task.py`) can run alongside
  US1's T019–T022, because the files are different.
- **Polish:** T037, T038 and T039 in parallel.

## Implementation strategy

All three stories ship together in 3.7 (spec). The order still delivers a usable state
at each checkpoint:

1. **Phases 1–2:** no visible change, and the existing suite passes.
2. **US1:** fail-fast cancellation on all runners. This alone answers NornFlow's
   blocking request, and it is the smallest state worth reviewing as a draft pull
   request.
3. **US2:** deadlines.
4. **US3:** progress.
5. **Polish:** docs, changelog, generated reference, full gate.

## Requirement coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T017, T020–T021 |
| FR-002 | T012, T017, T021 |
| FR-003 | T017, T021, T038 |
| FR-004 | T015–T016, T021–T022 |
| FR-005 | T015–T016, T019 |
| FR-006 | T015, T019 |
| FR-007 | T019, T031 |
| FR-008 | T019, T031, T035 |
| FR-009 | T017, T020 |
| FR-010 | T004, T010, T015 |
| FR-011 | T004, T010, T015 |
| FR-012 | T013, T015, T021 |
| FR-013 | T003, T006 |
| FR-014 | T016, T019 |
| FR-015 | T004, T015–T016, T019 |
| FR-016 | T004, T011, T031 |
| FR-017 | T003–T004, T006, T011 |
| FR-018 | T004, T011, T031 |
| FR-019 | T011, T016, T023, T026 |
| FR-020 | T004, T011 |
| FR-021 | T005, T007, T012 |
| FR-022 | T025, T029 |
| FR-023 | T025, T027 |
| FR-024 | T025–T027 |
| FR-025 | T025, T027 |
| FR-026 | T013, T015, T021 |
| FR-027 | T015, T021 |
| FR-028 | T013, T015, T019 |
| FR-029 | T038 |
| FR-030 | T031–T034 |
| FR-031 | T009, T031, T034 |
| FR-032 | T031, T034 |
| FR-033 | T031, T034 |
| FR-034 | T005, T007, T009, T014 |
| FR-035 | T005, T018, T021 |
| SC-001 | T015–T016 |
| SC-002 | T016, T026 |
| SC-003 | T025, T029 |
| SC-004 | T015–T017, T025–T026 |
| SC-005 | T005, T014, T024, T030, T036, T042 |
| SC-006 | T041 (CI matrix pending), T042 |
