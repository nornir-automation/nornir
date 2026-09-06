# Feature Specification: Asyncio Runner

**Feature Branch**: `dga/feat-async-spplb`

**Created**: 2026-09-06

**Status**: Draft

**Input**: User description: "Idea brief for nornir-automation/nornir#1085 (Async Runner), sharpened in a grilling session on 2026-09-02..06. Add opt-in native `asyncio` support next to the threaded runner: an `asyncio` runner plugin, `await nr.arun(task)` for callers already inside an event loop, a coroutine-aware `Task`, and an optional sibling `AsyncConnectionPlugin` protocol so async transports plug in first-class. Nothing changes unless the async runner is selected. Ships in 3.7 (MINOR) per Discussion #1091. Decisions taken during grilling: the connection-plugin protocol ships together with the runner as a single P1; synchronous tasks passed to the async entry points are rejected in this release with an error that names the follow-up issue; `Task.run()` keeps working inside an async task for backward compatibility; the runner is named `asyncio` / `AsyncioRunner`; `AsyncioRunner` is approved as an in-tree plugin but the `AsyncEcho` reference connection plugin lives under `tests/` as a fixture; cancellation propagates and records nothing, everything richer belongs to #1086; documentation is one executed notebook plus one prose page with the fixture's source included."

## User Scenarios & Testing *(mandatory)*

All four stories below ship together in the same release. The priorities express which
story the others depend on and which one alone would still justify the release, not a
plan to ship them separately.

### User Story 1 - Run async tasks from inside an event loop (Priority: P1)

An application developer whose program already runs an event loop (a web service
handler, a bot, a long-running daemon, an async test suite) selects the `asyncio` runner,
writes a task with `async def`, and runs it across the inventory with `await nr.arun(task)`.
The application's event loop keeps serving other work for the whole duration of the run,
and the developer gets back the same aggregated result object, with the same processor
events and the same failed-host bookkeeping, as a threaded run would have produced.
Inside the task, `await task.arun(subtask)` runs an async subtask with the same result
tree and failure semantics as `task.run()` does today.

**Why this priority**: This is the reason the feature exists. Without it Nornir cannot be
embedded in an async application at all, and none of the other stories are reachable.

**Independent Test**: Can be fully tested with an inventory of simulated hosts and a task
that awaits a short sleep in place of device I/O: the run completes, the result has one
entry per host, and a heartbeat coroutine running alongside is never starved. No
connection plugin is needed.

**Acceptance Scenarios**:

1. **Given** a `Nornir` object configured with `runner: asyncio` and a caller already
   inside a running event loop, **When** the caller awaits `nr.arun(async_task)`,
   **Then** every host in the inventory runs the task, at most `num_workers` hosts are
   in flight at any moment, and the returned object is an `AggregatedResult` with the
   same shape as `nr.run()` returns.
2. **Given** the same setup and a processor attached, **When** the run executes,
   **Then** the processor receives `task_started`, one `task_instance_started` and
   `task_instance_completed` per host, and `task_completed`, in the same order and with
   the same arguments as on a threaded run.
3. **Given** an async task that awaits `task.arun(async_subtask)`, **When** the subtask
   raises, **Then** the subtask's result is recorded as failed, the parent receives the
   same subtask error it would receive from `task.run()` today, and the host is marked
   failed in the aggregated result.
4. **Given** a run with `raise_on_error` left at its default, **When** one host fails,
   **Then** that host is added to `nr.data.failed_hosts` exactly as `nr.run()` would
   do, and a following `await nr.arun(...)` with the default `on_good`/`on_failed`
   skips it.
5. **Given** a `Nornir` configured with the `asyncio` runner, **When** the caller passes
   a plain `def` task to `nr.arun()` or to `task.arun()`, **Then** a named error is
   raised before any host starts, and its message says to define the task with
   `async def` or use a synchronous runner, and names the issue that tracks
   synchronous-task support in async runs.
6. **Given** a `Nornir` configured with the `serial` or `threaded` runner, **When** the
   caller passes an `async def` task to `nr.run()`, **Then** a named error is raised
   before any host starts, instead of today's behaviour of recording the un-awaited
   coroutine as a successful result.
7. **Given** a `Nornir` configured with the `asyncio` runner, **When** the caller calls
   the synchronous `nr.run()`, **Then** a named error is raised whose message points to
   `await nr.arun(...)`.
8. **Given** an async task that calls the synchronous `task.run(def_subtask)`, **When**
   the task runs, **Then** the subtask executes inline and its result is recorded as it
   is today (kept for backward compatibility with helpers that call `task.run`), and
   the documentation states that this is only appropriate for subtasks that do not
   block.
9. **Given** an async task that calls the synchronous `task.run(async_subtask)`,
   **When** the task runs, **Then** a named error is raised whose message points to
   `await task.arun(...)`.

---

### User Story 2 - Plug in an async transport as a connection plugin (Priority: P1)

A transport author whose library is async-native (SSH over an async SSH library, gNMI or
RESTCONF over an async HTTP client) implements the optional `AsyncConnectionPlugin`
contract — `aopen`, `aclose`, `connection` — alongside or instead of the existing
synchronous contract, registers it in the existing `nornir.plugins.connections` entry
point group, and users obtain the connection from an async task with
`await task.host.aget_connection(name, config)`. Existing synchronous connection plugins
are untouched and keep working exactly as they do today.

**Why this priority**: A runner nobody can connect through is a demonstration, not a
feature. The grilling session merged this into the first slice for that reason.

**Independent Test**: Can be fully tested with the standard-library-only `AsyncEcho`
test fixture plugin talking to a local echo server: an async task obtains the
connection, sends a payload, receives it back, and the connection is closed by
`aclose_connections`.

**Acceptance Scenarios**:

1. **Given** a plugin implementing `AsyncConnectionPlugin` registered under a name,
   **When** an async task awaits `task.host.aget_connection(name, config)`, **Then**
   the plugin's `aopen` is awaited once with the host's connection parameters, the
   established connection is returned, and a second call on the same host returns the
   cached connection without opening again.
2. **Given** a plugin that implements only the synchronous `ConnectionPlugin` contract,
   **When** an async task awaits `task.host.aget_connection(name, config)`, **Then** a
   named error is raised whose message says the plugin has no async members and points
   to `get_connection()` from a synchronous task.
3. **Given** a plugin that implements only `AsyncConnectionPlugin`, **When** a
   synchronous task calls `task.host.get_connection(name, config)`, **Then** the mirror
   named error is raised and points to `aget_connection()` from an async task.
4. **Given** a plugin implementing both contracts and a connection already opened on a
   host through the synchronous path, **When** an async task awaits
   `aget_connection` for the same name, **Then** the already-open connection is
   returned and `aopen` is not called: the per-host connection cache is keyed by name,
   not by kind.
5. **Given** an existing third-party synchronous connection plugin unchanged since
   before this release, **When** it is used from a synchronous task on any runner,
   **Then** its behaviour is identical to the previous release.

---

### User Story 3 - Clean up connections in an async context (Priority: P2)

The application developer wraps the run in `async with nr:` — or calls
`await nr.aclose_connections()` explicitly — and every connection opened during the run,
synchronous or asynchronous, is closed on exit, for hosts that succeeded and for hosts
that failed, with processors observing the cleanup the same way they observe any other
task.

**Why this priority**: Without it an async application leaks device sessions, but it
is only meaningful once stories 1 and 2 exist.

**Independent Test**: Open one synchronous and one asynchronous connection on a host
inside a run, mark a second host failed, exit the `async with` block, and verify every
host's connection table is empty and a recording processor saw the cleanup task.

**Acceptance Scenarios**:

1. **Given** connections open on several hosts, some of which are in `failed_hosts`,
   **When** the `async with nr:` block exits, **Then** the connections of good and
   failed hosts alike are closed.
2. **Given** a host holding one synchronous and one asynchronous connection, **When**
   `await nr.aclose_connections()` runs, **Then** the asynchronous one is closed by
   awaiting its `aclose` and the synchronous one by calling its `close`, and the host's
   connection table is empty afterwards.
3. **Given** a processor attached, **When** `await nr.aclose_connections()` runs,
   **Then** the processor sees a `task_started` event for the cleanup task, and the
   cleanup honours `on_good` and `on_failed` like any other task.
4. **Given** a `Nornir` configured with the `asyncio` runner, **When** the caller uses
   the synchronous `with nr:` or calls `nr.close_connections()`, **Then** a named error
   is raised whose message points to `aclose_connections()`.

---

### User Story 4 - Cancel a run in progress (Priority: P3)

The application that owns the event loop cancels the awaiting `arun` — a client
disconnected, a shutdown began — while hosts are still in flight. The run stops, nothing
half-finished is recorded as a result or as a failed host, and no host work is left
running in the background.

**Why this priority**: This is the baseline behaviour any async caller expects, and the
only cancellation behaviour this release defines. Richer semantics (partial results,
timeouts, a cooperative cancel API) are the subject of #1086.

**Independent Test**: Start a run whose task awaits a long sleep, cancel the awaiting
coroutine after the first host has started, and assert the cancellation propagates, no
task coroutine is still pending, `failed_hosts` is unchanged, and no `task_completed`
event was emitted.

**Acceptance Scenarios**:

1. **Given** a run with twenty hosts in flight, **When** the caller cancels the
   `arun` coroutine, **Then** every in-flight host is cancelled, the cancellation
   propagates to the caller, and no aggregated result is returned.
2. **Given** the same cancellation, **When** the caller inspects state afterwards,
   **Then** `nr.data.failed_hosts` is unchanged, no processor received
   `task_completed`, and no host coroutine is still pending.

---

### Edge Cases

- A `def` task or subtask reaches an async entry point, or an `async def` task reaches a
  synchronous one, at any of the seven surfaces (`nr.arun`, `nr.run`, `task.arun`,
  `task.run`, `nr.close_connections`, `host.get_connection`, `host.aget_connection`):
  a named error is raised before any host starts, and the message names the entry point
  to use instead.
- The caller cancels `arun` mid-run: cancellation propagates, nothing is recorded.
- A host holds a mix of synchronous and asynchronous connections at cleanup: both kinds
  are closed.
- A connection was opened by a synchronous task and is later requested from an async
  task under the same name: the cached connection is returned, nothing is reopened.
- Two concurrent `aget_connection` calls for the same host and name from inside one task
  (the user fans out inside the task): the second call raises rather than opening a
  second connection. Taken as-is from the proposal.
- A synchronous processor is attached to an async run: it works, but blocks the loop
  while its hook runs. Documented as a known limitation, owned by #1090.
- A run with zero selected hosts: behaves as `nr.run()` does today (a warning is
  logged, an empty aggregated result is returned).
- `num_workers` larger than the host count: every host runs concurrently; no error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `asyncio` runner MUST be selectable through the existing runner
  configuration (`runner.plugin: asyncio`, with `num_workers` under `runner.options`)
  and through `nr.with_runner(...)`, and MUST accept the same `num_workers` option with
  the same default value (20) as the threaded runner.
- **FR-002**: `Nornir.arun()` MUST accept the same arguments as `Nornir.run()`
  (`task`, `raise_on_error`, `on_good`, `on_failed`, `name`, task keyword arguments) and
  MUST return an `AggregatedResult` of the same shape.
- **FR-003**: `Nornir.arun()` MUST apply `raise_on_error` and MUST update
  `data.failed_hosts` exactly as `Nornir.run()` does.
- **FR-004**: The `asyncio` runner MUST limit the number of hosts in flight to
  `num_workers`.
- **FR-005**: `Nornir.arun()` and `Task.arun()` MUST raise a named error when given a
  task that is not defined with `async def`; the message MUST name the issue tracking
  synchronous-task support in async runs.
- **FR-006**: The `serial` and `threaded` runners MUST raise a named error when given an
  `async def` task, instead of storing the un-awaited coroutine as a successful result.
- **FR-007**: `Nornir.run()` and `Nornir.close_connections()` on a `Nornir` configured
  with the `asyncio` runner MUST raise a named error pointing to `arun()` /
  `aclose_connections()` respectively; the synchronous `with nr:` MUST raise the same
  error on exit.
- **FR-008**: `Task.arun()` MUST provide the same result-tree and failure semantics as
  `Task.run()`: the subtask's result is appended to the parent's results, and a failed
  subtask raises the same subtask error in the parent.
- **FR-009**: `Task.run()` called inside an async task MUST continue to execute a `def`
  subtask inline, as it does today.
- **FR-010**: `Task.run()` called inside an async task with an `async def` subtask MUST
  raise a named error pointing to `Task.arun()`.
- **FR-011**: A new optional `AsyncConnectionPlugin` contract MUST exist with `aopen`
  and `aclose` taking the same parameters, in the same order, as `open` and `close`,
  plus the `connection` property. The existing `ConnectionPlugin` contract MUST NOT
  change. Plugins MUST register in the existing `nornir.plugins.connections` entry-point
  group.
- **FR-012**: `Host` MUST provide `aget_connection`, `aopen_connection`,
  `aclose_connection` and `aclose_connections`, mirroring the existing synchronous
  methods, sharing the same per-host connection cache keyed by connection name.
- **FR-013**: `Host.aget_connection()` on a plugin without async members MUST raise a
  named error pointing to `get_connection()`; `Host.get_connection()` on a plugin
  without synchronous members MUST raise the mirror error pointing to
  `aget_connection()`.
- **FR-014**: `Host.aclose_connections()` MUST close every open connection on the host,
  awaiting `aclose` on async-capable plugins and calling `close` on synchronous ones.
- **FR-015**: `Nornir.aclose_connections()` MUST run as a task through `arun()` so that
  processors observe it and `on_good`/`on_failed` apply; `async with nr:` MUST close
  the connections of good and failed hosts on exit.
- **FR-016**: Cancelling `Nornir.arun()` MUST cancel every in-flight host, propagate
  the cancellation to the caller, and MUST NOT record a result, update
  `failed_hosts`, or emit `task_completed`.
- **FR-017**: Processors attached to an async run MUST receive the same events, in the
  same order, with the same arguments as on a synchronous run.
- **FR-018**: A standard-library-only reference async connection plugin (`AsyncEcho`)
  MUST exist as a test fixture, exercising the complete async connection path in the
  test suite on every supported platform; it MUST NOT ship in the installed package.
- **FR-019**: Documentation MUST include an executed how-to notebook demonstrating
  runner selection, an async task, `arun`, `async with`, and the named errors as real
  output, and a prose how-to page for plugin authors that includes the source of the
  reference fixture and the two rules for async members (`aopen`/`aclose` must not
  block; `aclose` must be safe to call more than once).
- **FR-020**: No existing public signature, protocol member, default value or
  entry-point name MAY change; the pre-existing test suite MUST pass unmodified.

### Key Entities

- **Asyncio runner**: A runner plugin, registered as `asyncio`, that executes a task
  over the selected hosts concurrently on the caller's event loop, bounded by
  `num_workers`. New; joins `serial` and `threaded` as an in-tree runner (approved
  under Constitution principle II).
- **Async entry points on `Nornir`**: `arun`, `aclose_connections`, and async context
  manager support. Existing entity, new members; the synchronous members are unchanged.
- **Coroutine-aware `Task`**: `astart` and `arun` as async twins of `start` and `run`,
  sharing the same result and failure semantics. Existing entity, new members.
- **`AsyncConnectionPlugin` contract**: An optional sibling of `ConnectionPlugin` with
  `aopen`, `aclose` and `connection`. A plugin may satisfy one or both contracts. New.
- **Async connection methods on `Host`**: `aget_connection`, `aopen_connection`,
  `aclose_connection`, `aclose_connections`, over the existing per-host connection
  cache. Existing entity, new members.
- **Named errors**: One error per wrong sync/async combination, each message naming the
  entry point to use instead. New.
- **`AsyncEcho` fixture**: A standard-library-only async connection plugin living in the
  test suite, whose source is included in the plugin-author documentation. New,
  test-only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The complete pre-existing test suite passes without modification once the
  feature is merged, and upgrading requires zero code changes for users who do not
  select the `asyncio` runner.
- **SC-002**: During a run over 100 hosts whose task awaits 100 ms of simulated I/O,
  another coroutine sharing the caller's event loop is never starved for more than
  50 ms.
- **SC-003**: A run over 1,000 hosts, each awaiting 100 ms of simulated I/O, with
  `num_workers=1000`, completes in under 2 seconds of wall-clock time, and the number
  of live threads in the process is the same before and after the run.
- **SC-004**: Every wrong sync/async combination listed in the edge cases raises a
  named error before a single per-host event is emitted.
- **SC-005**: A plugin author can add async support to an existing synchronous
  connection plugin by adding exactly two methods (`aopen`, `aclose`) and changing
  nothing else — no registration change, no configuration change.
- **SC-006**: The how-to notebook executes in the documentation build and its stored
  output matches the run on every documentation build.

## Assumptions

- `num_workers` protects the devices, not the client; the default stays 20 on the
  `asyncio` runner. Users who want the scaling benefit raise it explicitly.
- Keeping `Task.run()` working inside an async task means `def` subtasks run inline on
  the event loop at the caller's responsibility. This was chosen for backward
  compatibility with helper code that calls `task.run` internally, in full knowledge
  that it cannot be withdrawn later. The follow-up on synchronous tasks in async runs
  therefore covers thread-backed execution and its opt-in surface, not inline
  execution.
- Until the follow-up issue on synchronous tasks in async runs is opened, the error
  messages of FR-005 reference #1085; the number is replaced once the follow-up issue
  exists, and opening it is a precondition of merging this feature.
- Whether a connection plugin supports the async path is determined structurally, from
  the presence of its async members, consistent with the structural `Protocol` design
  of the existing contracts.
- Processors are called synchronously on the async path. A processor that performs slow
  I/O blocks the loop while it runs; #1090 addresses that separately.
- The release is only useful in practice to users with genuinely async I/O until the
  synchronous-task follow-up lands; this is accepted for the alpha.
- Exact exception class names and whether they share a common base are settled at
  planning time; the specification only requires that each is a distinct, named error
  whose message names the correct entry point.
- Debuggability with stock Python tooling is preserved: a breakpoint inside an
  `async def` task pauses the run like any debugger would, and a failed host's
  traceback contains the user's own task code.
- Every supported Python version (3.10 to 3.14) and platform (Linux, macOS, Windows)
  runs the full async test path, including the `AsyncEcho` fixture.

### Out of Scope

- Synchronous tasks run in threads inside an async run, caller flags, or author
  markers declaring a task non-blocking (follow-up issue).
- Streaming, timeouts, cooperative cancellation, partial results on cancel, and whether
  future runner capabilities come as sync/async pairs or one runner with two modes
  (#1086).
- Async inventory plugins (#1087). Async processors (#1090).
- trio or `anyio` support; any new runtime dependency.
- Migrating the plugin ecosystem, or shipping a usable async transport in the core
  package.
- A major-version upgrade guide: the release is additive and nothing breaks.
