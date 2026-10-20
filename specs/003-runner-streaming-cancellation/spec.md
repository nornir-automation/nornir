# Feature Specification: Runner Streaming, Cancellation, and Timeouts

**Feature Branch**: `dga/feat-runner-xoh8k`

**Created**: 2026-10-18

**Status**: Draft

**Input**: Runner enhancements proposal
[nornir-automation/nornir#1086](https://github.com/nornir-automation/nornir/issues/1086),
with the NornFlow feedback in
[its first comment](https://github.com/nornir-automation/nornir/issues/1086#issuecomment-6038849471),
refined in a grilling session on 2026-10-18. Add an opt-in API for long-running work: start
a run in the background and receive a handle, read each host's final result as it
finishes, cancel the run, set per-host and per-run deadlines, and let tasks report progress
by yielding partial results. The API is one contract across runners; each runner declares
how deeply it can deliver cancellation. Builds on the asyncio runner from
[spec 001](../001-asyncio-runner/spec.md). Target release: 3.7, together with #1085.

## User Scenarios & Testing *(mandatory)*

The primary user is a developer of an application or framework built on Nornir (NornFlow,
a web service, a bot). Today they cannot stop hosts that are already running after one host
fails, cannot set a deadline, and cannot handle each host's result as it finishes. The
secondary user is a script author who runs long operations and wants live progress and
deadlines; they use the same API.

All three stories ship together in 3.7. The priorities show which story the others depend
on: P2 reuses the cancellation path of P1, and P3 is independent of both. They are not a
plan to ship the stories separately.

### User Story 1 - Abort the remaining hosts after a failure (Priority: P1)

A framework developer starts a run with `nr.submit(task)` (or `await nr.asubmit(task)` on
the asyncio runner) and receives a run handle immediately. They read each host's final
`Result` through `handle.results()` in the order hosts finish. When the first host fails,
they call `handle.cancel()`. No further host starts, hosts already running stop at their
next checkpoint, and `handle.result()` returns an `AggregatedResult` in which every
selected host has exactly one entry.

**Why this priority**: This is the gap NornFlow names: its fail-fast policy can stop later
tasks, but not hosts already inside the current run. It also builds the cancellation and
recording rules that timeouts reuse.

**Independent Test**: Run a task over simulated hosts where one host fails quickly and the
others loop over a short sleep with a checkpoint on each iteration. Cancel on the first
failed result and assert that every host has exactly one entry, that hosts not yet started
never ran the task body, and that cancelled hosts carry `TaskCancelledError`.

**Acceptance Scenarios**:

1. **Given** a run of a task across 20 hosts on `ThreadedRunner` or `AsyncioRunner`, where
   the task reaches a checkpoint between steps, **When** the first host returns a failed
   `Result` and the caller calls `cancel()`, **Then** no host starts the task after that
   point, hosts already running stop at their next checkpoint, and the final
   `AggregatedResult` has one entry for each of the 20 hosts: a finished `Result`, or a
   failed `Result` carrying `TaskCancelledError`.
2. **Given** the same cancelled run with `raise_on_error` off, **When** the run finishes,
   **Then** every cancelled host is in `nr.data.failed_hosts`, even if the caller never
   calls `handle.result()`.
3. **Given** a processor attached to the run and `raise_on_error` off, **When** the run
   is cancelled, **Then** the processor receives `task_started` once before `submit`
   returns, then `task_instance_started` and `task_instance_completed` for every host
   (including hosts that never started), then `task_completed` once. With
   `raise_on_error` on and a failed host, `task_completed` does not fire, as with
   `run()` today.
4. **Given** a run with `raise_on_error` on and one failed host, **When** the caller
   iterates `handle.results()`, **Then** the failed `Result` is yielded without raising;
   **When** the caller calls `handle.result()`, **Then** `NornirExecutionError` is raised
   there.
5. **Given** a task that wraps its subtask calls in `try: ... except Exception:`, **When**
   the run is cancelled while that host is running, **Then** the cancellation is not
   caught by the handler and the host is recorded as cancelled.
6. **Given** a running handle, **When** two threads iterate `handle.results()` and a third
   calls `cancel()` twice, **Then** both iterators yield the same final results in the
   same completion order, and neither `cancel()` call raises.
7. **Given** the caller cancels the coroutine awaiting `nr.arun()` (asyncio cancellation),
   **When** the cancellation propagates, **Then** the behaviour of spec 001 FR-016 holds
   unchanged: nothing is recorded.
8. **Given** a `run_stream` loop that leaves on the first failed result, **When** the same
   code runs on `SerialRunner` and on `ThreadedRunner`, **Then** on both runners no host
   starts after the loop is left, and the run records every selected host with the same
   rules. On `SerialRunner`, every task runs on the caller's thread.
9. **Given** `SerialRunner`, **When** the caller calls `nr.submit(task)`, **Then**
   `RunnerCapabilityError` is raised, and its message names `run_stream`.

---

### User Story 2 - Deadlines per host and per run (Priority: P2)

A developer sets `per_host_timeout` and `timeout` (whole run), in seconds, either on the
runner (constructor or `runner.options`) or per run through a run-options object passed to
`submit` or `run_stream`. A host that exceeds its deadline is stopped and recorded as
failed with `TaskTimeoutError`, and the other hosts are not affected. A stuck or
unreachable device no longer blocks the whole run.

**Why this priority**: A deadline is a cancellation triggered by a clock instead of the
caller, recorded with a different error. It depends on User Story 1.

**Independent Test**: Run a task where one simulated host sleeps past the deadline and the
others finish quickly; assert the slow host carries `TaskTimeoutError`, the fast hosts
carry their own results, and the call returns within the time bound.

**Acceptance Scenarios**:

1. **Given** a run on `ThreadedRunner` with `timeout=T`, where one host is blocked in an
   I/O call that never returns, **When** T expires, **Then** the caller receives the
   `AggregatedResult` within T + 1 second, the blocked host and every host that had not
   started are recorded with `TaskTimeoutError`, and the other hosts keep their own
   results.
2. **Given** a runner configured with `per_host_timeout=600` and a per-run options object
   with `per_host_timeout=60`, **When** the run starts, **Then** the per-run value applies.
3. **Given** a runner configured with `per_host_timeout`, **When** the caller uses plain
   `nr.run(task)`, **Then** the deadline applies and `run()` returns the usual
   `AggregatedResult`.
4. **Given** a task with its own parameter named `timeout`, **When** the caller runs
   `nr.run(task, timeout=30)`, **Then** the value reaches the task, exactly as today.
5. **Given** `AsyncioRunner` and a host awaiting a call with no checkpoint in the task,
   **When** its deadline passes, **Then** the host is interrupted at that await and
   recorded with `TaskTimeoutError`.
6. **Given** `SerialRunner` configured with `per_host_timeout`, **When** a host passes its
   deadline and then reaches a checkpoint, **Then** the host is recorded with
   `TaskTimeoutError` and the next host starts. A host blocked in a call that does not
   return delays the caller until the call returns.

---

### User Story 3 - Progress from long tasks (Priority: P3)

A task author writes the task as a generator (`def` with `yield`) or, on the asyncio
runner, as an async generator (`async def` with `yield`). Each yielded `PartialResult`
reports a stage ("uploading image", "rebooting") and an optional progress fraction. A
`def` generator's `return` value is the final `Result`, as today. An async generator
cannot `return` a value in Python, so it ends by yielding its final `Result`. The caller
watches events live with
`nr.run_stream(task)` / `nr.astream(task)` or `handle.events()`, reads the latest progress
per host with `handle.progress()`, and processors receive each partial result through a
new optional hook.

**Why this priority**: Progress gives feedback during long operations, but neither
cancellation nor deadlines depend on it.

**Independent Test**: Run a generator task that yields two partial results and returns a
`Result`; assert the stream delivers two partial results and one final result per host, a
progress processor receives the same partial results, and the host's `MultiResult`
contains only the final `Result`.

**Acceptance Scenarios**:

1. **Given** a generator task that yields "uploading" then "rebooting" before returning a
   `Result`, **When** it runs with `run_stream`, **Then** the caller receives two
   `PartialResult` events and one final `Result` per host.
2. **Given** the same task and a processor that defines `task_instance_progress`, **When**
   it runs with plain `nr.run()`, **Then** the processor receives both partial results,
   and the host's final `MultiResult` contains only the `Result`.
3. **Given** a processor that does not define `task_instance_progress`, **When** a
   generator task runs, **Then** that processor is never called with a partial result and
   behaves exactly as today.
4. **Given** a `run_stream` loop, **When** the caller leaves it with `break` or an
   exception, **Then** the run is cancelled.
5. **Given** a running handle, **When** a second consumer calls `handle.events()` after
   some hosts reported progress, **Then** it receives only events produced after the call,
   and `handle.progress()` returns the latest `PartialResult` of each host.
6. **Given** a task that calls a generator subtask with `task.run()`, **When** the subtask
   yields, **Then** the partial results reach the host's stream tagged with the subtask
   name, and `task.run()` still returns the `MultiResult` as today.
7. **Given** an async generator task, **When** it is run on a synchronous runner, **Then**
   the named error from spec 001 is raised; the same applies to a `def` generator on
   `AsyncioRunner`.

### Edge Cases

- A task catches the cancellation with `except Exception`: not caught, because the error
  base subclasses `BaseException`. With `except BaseException` or a bare `except:`, the
  next checkpoint raises again.
- A thread on a threaded runner is blocked in I/O when its deadline passes: the run returns
  on time, the host is recorded as timed out, and the thread keeps its worker slot until
  the call returns.
- `cancel()` is called twice, from another thread, or after the run finished: no effect,
  nothing raised.
- A handle is never consumed: the run still finishes and nothing is raised. When
  `raise_on_error` is off, `failed_hosts` is updated and `task_completed` fires. When it
  is on and a host failed, neither happens, as with `run()` today.
- `cancel()` is called on a threaded run while a host is blocked in a call that does
  not return, and no deadline is set: the host is recorded as cancelled only when the
  call returns and the task reaches its next checkpoint, so `result()` waits until
  then. Only a deadline (`per_host_timeout` or `timeout`) frees the caller from a
  blocked host.
- `results()` is called after some hosts finished: the finished hosts are replayed first,
  in completion order.
- The run-level deadline expires before some hosts start: those hosts are recorded with
  `TaskTimeoutError` and marked as never started.
- `cancel()` is called before any host has started: every host is recorded as cancelled
  and never started.
- A run selects zero hosts: `submit` returns a handle that is already done, and its
  `result()` is an empty `AggregatedResult`, as `run()` returns today.
- A task with `yield` previously returned its generator object as a successful `Result`
  without running its body; it now runs as a progress-reporting task.
- The coroutine awaiting `handle.result()` is cancelled: only the waiting stops; the run
  continues.

## Requirements *(mandatory)*

### Functional Requirements

**Same behaviour on all runners**

- **FR-001**: The same task and the same calling code MUST run unchanged on `SerialRunner`
  and `ThreadedRunner` through `run()` and `run_stream()`, including runner deadlines and
  cancellation by leaving a `run_stream` loop. The final `AggregatedResult` has the same
  shape on both, and cancelled and timed-out hosts are recorded the same way.
- **FR-002**: `SerialRunner` MUST run every task on the caller's thread, through every
  entry point it supports, so that a debugger breakpoint inside a task works. It delivers
  cancellation and deadlines at `checkpoint` depth.
- **FR-003**: `nr.submit()` on `SerialRunner` MUST raise `RunnerCapabilityError`, with a
  message that names `run_stream` as the entry point to use instead. The documentation
  MUST list every part of the new API that behaves differently on `SerialRunner`.

**Starting and reading a run**

- **FR-004**: Users MUST be able to start a run in the background with `nr.submit(...)`
  (synchronous tasks on `ThreadedRunner`) or `await nr.asubmit(...)` (asynchronous tasks on `AsyncioRunner`)
  and receive a run handle immediately.
- **FR-005**: The run handle MUST provide an identifier, a completion flag, final results
  in completion order, live events, the latest progress per host, cancellation, and a
  blocking (or awaitable) call that returns the usual `AggregatedResult`.
- **FR-006**: `handle.results()` MUST be callable any number of times, from any thread.
  Each call first replays the hosts already finished in completion order, then waits for
  the rest.
- **FR-007**: `handle.events()` MUST deliver only the events produced after it is called.
- **FR-008**: `handle.progress()` MUST return the latest `PartialResult` of each host, and
  the handle MUST keep no other partial result.
- **FR-009**: Users MUST be able to consume a run live with `nr.run_stream(...)` or
  `nr.astream(...)`. Leaving such a loop early (by `break` or by an exception) MUST cancel
  the run. Leaving a loop over a handle's iterators MUST NOT cancel it.

**How cancelled and timed-out hosts are recorded**

- **FR-010**: Every selected host MUST end with exactly one final `Result`. A host that was
  running or had not started when a cancellation or deadline arrived MUST be recorded as a
  failed `Result` carrying `TaskCancelledError` or `TaskTimeoutError`; a host that never
  started is marked as such.
- **FR-011**: Processors MUST receive `task_instance_started` and `task_instance_completed`
  for every selected host, including hosts cancelled or timed out before they started.
- **FR-012**: When `raise_on_error` is off, cancelled and timed-out hosts MUST be added to
  `nr.data.failed_hosts` once, when the run finishes, whether or not the caller ever reads
  the final result.
- **FR-013**: `TaskCancelledError` and `TaskTimeoutError` MUST be distinct types with a
  common base, so callers can tell "cancelled" from "timed out" from "task failed" without
  reading messages.
- **FR-014**: `handle.cancel()` MUST record every host. Asyncio cancellation of the
  coroutine awaiting `nr.arun()` MUST keep the behaviour of spec 001 FR-016 (nothing
  recorded). Cancelling the coroutine awaiting the handle's final result MUST stop only
  the waiting.
- **FR-015**: `cancel()` MUST be safe to call from any thread, any number of times,
  including after the run has finished.

**How cancellation is delivered**

- **FR-016**: Users MUST be able to mark a cancellation point in a task with
  `task.checkpoint()`; every `yield` in a progress-reporting task MUST also be a
  checkpoint.
- **FR-017**: The common base of `TaskCancelledError` and `TaskTimeoutError` MUST subclass
  `BaseException`, so that `except Exception` does not catch it.
- **FR-018**: Once a host is cancelled or timed out, every later checkpoint for that host
  MUST raise again.
- **FR-019**: On `AsyncioRunner`, cancellation and deadlines MUST interrupt a host at the
  await it is waiting on, and the host's final `Result` MUST carry the same error types as
  on the threaded runners.
- **FR-020**: A cancellation delivered inside a subtask MUST propagate into the parent
  task.
- **FR-021**: Each runner MUST declare its cancellation depth: `checkpoint` (delivered at
  the next checkpoint) or `immediate` (delivered at the current await). No call fails
  because of the depth.
- **FR-022**: On a threaded runner, a run whose deadline has passed MUST return to the
  caller on time even when a host is blocked in a call that does not return.

**Where deadlines are set**

- **FR-023**: `Nornir.run()` and `Nornir.arun()` MUST keep their current signatures. No new
  keyword argument may take a name away from task arguments.
- **FR-024**: Runners MUST accept `per_host_timeout` and `timeout` as runner options
  (constructor or `runner.options`), applying to every entry point, including `run()`.
- **FR-025**: `submit`, `asubmit`, `run_stream`, and `astream` MUST accept a run-options
  object, separate from task arguments, whose deadlines override the runner's.

**Lifecycle of a background run**

- **FR-026**: A run started with `submit`, `asubmit`, `run_stream`, or `astream` MUST call
  the same processor hooks as `run()`, in the same order and with the same arguments.
  `task_started` MUST fire before `submit` returns.
- **FR-027**: The hosts of a background run MUST be selected when it is started, from
  `failed_hosts` as it is at that moment.
- **FR-028**: With `raise_on_error` on, `NornirExecutionError` MUST be raised only from the
  handle's final-result call. `results()` and `events()` MUST NOT raise for a failed host.
- **FR-029**: The documentation MUST state on which thread each processor hook runs for a
  background run.

**Progress reporting**

- **FR-030**: A `def` task containing `yield` MUST run as a progress-reporting task on the
  synchronous runners. An `async def` task containing `yield` MUST run as one on
  `AsyncioRunner`. Wrong combinations MUST raise the named errors of spec 001. A yielded
  `Result` MUST end the task with that result; it is the only way an async generator can
  give its final result.
- **FR-031**: Each yielded `PartialResult` MUST reach the stream, `handle.events()`,
  `handle.progress()`, and every processor that defines `task_instance_progress`.
  Processors that do not define it MUST NOT be called with it.
- **FR-032**: A host's final `MultiResult` MUST contain only `Result` objects. A
  `PartialResult` MUST NOT mark a host as failed.
- **FR-033**: A partial result yielded by a subtask MUST reach the host's stream tagged
  with the subtask name, and `task.run()` MUST still return the subtask's `MultiResult`.

**Compatibility**

- **FR-034**: `RunnerPlugin`, `AsyncRunnerPlugin`, and `Processor` MUST NOT change. The new
  capabilities MUST be expressed as separate optional protocols, so that existing
  third-party runners and processors keep working without changes.
- **FR-035**: A third-party runner that does not implement the new protocols MUST raise
  `RunnerCapabilityError` naming the missing capability when a caller uses an entry point
  that needs it.

### Key Entities

- **Result, MultiResult, AggregatedResult** (existing, unchanged): the final result of a
  host, the results of one host's task tree, and the results of a run.
- **Task** (existing): gains `checkpoint()`, the explicit cancellation point.
- **SerialRunner, ThreadedRunner, AsyncioRunner** (existing): gain the new entry points,
  the deadline options, and a declared cancellation depth.
- **PartialResult** (new): an intermediate result of one host: the host, any value, and an
  optional progress fraction between 0 and 1. It has no failed, changed, or diff state.
- **Run handle** (new): one background run inside one process. Identifier, completion
  flag, final results in completion order, live events, latest progress per host,
  cancellation, and the final `AggregatedResult`. It does not survive the process.
- **Run options** (new): per-run settings, separate from task arguments: per-host deadline
  and run deadline.
- **TaskCancelledError, TaskTimeoutError, and their common base** (new): the errors carried
  by the final `Result` of a cancelled or timed-out host.
- **Streaming runner protocols and progress processor protocol** (new): optional sibling
  contracts next to `RunnerPlugin`, `AsyncRunnerPlugin`, and `Processor`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On `ThreadedRunner` and `AsyncioRunner`, after a cancellation, no host starts
  its task. On a 100-host run with one checkpoint per second per task, the run is finished
  within 2 seconds of the cancellation.
- **SC-002**: On `AsyncioRunner`, a host waiting in an awaited call is stopped within 0.1
  seconds of a cancellation or of its deadline, with no checkpoint in the task.
- **SC-003**: On `ThreadedRunner`, a run with a run deadline of T seconds returns to the
  caller within T + 1 seconds, even if a host is blocked in a call that never returns.
- **SC-004**: The final result of every cancelled or timed-out run contains exactly one
  entry per selected host, for every combination of runner (threaded, asyncio), entry
  point (`run`, `submit`, `run_stream`), and trigger (cancel, per-host deadline, run
  deadline), and for `SerialRunner` with `run` and `run_stream`.
- **SC-005**: The existing test suite, the existing documentation notebooks, and a
  third-party runner and processor written against today's protocols pass without changes.
- **SC-006**: The timing criteria SC-001 to SC-003 hold on every supported platform
  (Linux, macOS, Windows) and Python version (3.10 to 3.14) in CI.

## Clarifications

### Session 2026-10-19

- Q: How does `SerialRunner` support the new API while every task stays on the caller's
  thread? → A: `SerialRunner` supports `run_stream` and runner deadlines, delivered at
  checkpoints, and cancellation by leaving the `run_stream` loop. `submit` raises
  `RunnerCapabilityError` and names `run_stream`. A lazy handle that runs hosts while the
  caller reads it was considered and not chosen.

### Session 2026-10-20

- Q: How does an `async def` progress task give its final result, since an async
  generator cannot `return` a value? → A: It yields its final `Result`, which ends the
  task. A `def` generator may do the same, or `return` its result. The `async def`
  example in #1086 (`return Result(...)` inside an async generator) is a `SyntaxError`.
  Found in code review of the implementation.
- Q: When does a stream or a `results()` loop end on a background run? → A: After the
  run is finalized, so that `failed_hosts` is updated, `task_completed` has fired and
  the handle is done when the loop ends, on every runner (FR-001, FR-012, FR-026). Found
  in code review: the loop ended when the last host was recorded, before finalization.

## Assumptions

- This builds on `AsyncioRunner` and `AsyncRunnerPlugin` from spec 001 as shipped: one
  runner class per execution mode, with a separate async protocol. Question 1 of #1085 is
  settled by that implementation.
- Tasks that need responsive cancellation on threaded runners add checkpoints. Without
  them, a cancellation waits until the task ends. Tasks built on blocking libraries are
  advised to call `task.checkpoint()` between commands.
- Progress is meant for stages, not for every line of output. No overhead target is set
  per partial result.
- The change to tasks containing `yield` is treated as a bug fix in the 3.7 MINOR release,
  without a deprecation period, and named in `CHANGELOG.rst`. The current behaviour
  reports success for a task whose body never ran. A task that wants to return a
  generator as data wraps it in a `Result`.
- All additions are new names and new optional protocols; no existing protocol or
  signature changes, so the feature fits a MINOR release under constitution principle VI.
- No new runtime dependency and no new in-tree plugin.
- Exact names of the run-options object, the protocols, and the depth declaration are
  settled during planning; the names in this spec follow the proposal.
- Events carry plain fields (host by name, plain values, errors as type and message), so
  that a later out-of-process runner plugin can serialise them.
- Documentation adds a how-to notebook for cancellation, deadlines, and progress, executed
  by `make nbval`.

### Out of Scope

- Detached runs that survive a process restart, and re-attaching from another process.
- Force-stopping a thread blocked in an I/O call.
- A run store or event sink defined by the core. The documentation shows an example
  processor that records events, not a convention.
- Serialisation formats for a distributed runner.
- Async processor hooks
  ([#1090](https://github.com/nornir-automation/nornir/issues/1090)); the new progress
  hook is synchronous.
- Orchestration between tasks: canary rollouts, batches, retries.
- Keeping partial results in `MultiResult`, including as an opt-in.
- Deadline arguments on `run()` and `arun()`.
- Background runs (`submit`) on `SerialRunner`.
- Changes needed in NornFlow (task discovery of generator tasks, its wrapper hooks).
