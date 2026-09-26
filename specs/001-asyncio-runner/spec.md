# Feature Specification: Asyncio Runner

**Feature Branch**: `dga/feat-async-spplb`

**Created**: 2026-09-06

**Status**: Draft

**Input**: Async runner feature from nornir-automation/nornir#1085, refined on
2026-09-02..06 and updated on 2026-09-13: add opt-in native asyncio task execution and
the capability-aware `CapabilityConnectionPlugin` contract with its own
`CapabilityConnectionPluginRegister`. The new registry supports synchronous plugins,
asyncio plugins, and plugins supporting both. Preserve `ConnectionPlugin` and
`ConnectionPluginRegister` as the legacy compatibility path. All four stories ship
together in 3.7 (MINOR) per Discussion #1091. `AsyncioRunner` is approved in-tree;
the reference connection plugin remains a test fixture.

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
   `task_instance_completed` per host, and `task_completed`, with the same arguments
   and per-host ordering as on a threaded run. Events from different hosts may interleave.
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
   raised before any host starts for `nr.arun()`, or before the subtask starts for
   `task.arun()`, and its message says to define the task with
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

### User Story 2 - Register a capability-aware connection plugin (Priority: P1)

A transport author implements `CapabilityConnectionPlugin`, reports whether the plugin
supports synchronous execution, asyncio execution, or both, and registers it once in
`CapabilityConnectionPluginRegister`. Users obtain connections by name through
`task.host.get_connection(name, config)` or
`await task.host.aget_connection(name, config)`, according to the declared capabilities.
The new contract serves synchronous and asynchronous transports alike. Existing plugins
continue using `ConnectionPlugin` and `ConnectionPluginRegister` without migration or
a new capability method.

**Why this priority**: A runner nobody can connect through is a demonstration, not a
feature. The grilling session merged this into the first slice for that reason.

**Independent Test**: Can be fully tested with the standard-library-only `AsyncEcho`
test fixture plugin talking to a local echo server: an async task obtains the
connection from a plugin registered in the new registry, sends a payload, receives it
back, and the connection is closed by `aclose_connections`. Synchronous-only and
dual-capability test plugins additionally prove all capability combinations, alongside
an unchanged legacy plugin.

**Acceptance Scenarios**:

1. **Given** a `CapabilityConnectionPlugin` declaring asyncio support and registered
   under a name in `CapabilityConnectionPluginRegister`,
   **When** an async task awaits `task.host.aget_connection(name, config)`, **Then**
   the plugin's `aopen` is awaited once with the host's connection parameters, the
   established connection is returned, and a second call on the same host returns the
   cached connection without opening again.
2. **Given** a legacy `ConnectionPlugin` or a capability-aware plugin declaring only
   synchronous support,
   **When** an async task awaits `task.host.aget_connection(name, config)`, **Then** a
   named error is raised whose message says the plugin does not support asyncio and points
   to `get_connection()` from a synchronous task.
3. **Given** a capability-aware plugin declaring only asyncio support, **When** a
   synchronous task calls `task.host.get_connection(name, config)`, **Then** the mirror
   named error is raised and points to `aget_connection()` from an async task.
4. **Given** a capability-aware plugin declaring both capabilities and a connection already opened on a
   host through the synchronous path, **When** an async task awaits
   `aget_connection` for the same name, **Then** the already-open connection is
   returned and `aopen` is not called. The reverse direction also reuses the connection:
   there is one logical connection per host and name, regardless of execution mode.
5. **Given** an existing third-party synchronous connection plugin unchanged since
   before this release and registered in `ConnectionPluginRegister`, **When** it is
   used through the existing synchronous execution path,
   **Then** its behaviour is identical to the previous release.
6. **Given** a synchronous-only capability-aware plugin registered in the new registry,
   **When** a synchronous task requests its connection, **Then** `open` is called with
   the resolved host parameters, repeated requests reuse the connection, and synchronous
   cleanup calls `close` without invoking an async operation.
7. **Given** one plugin for each supported capability combination, **When** the plugin's
   capability method is queried before opening a connection, **Then** it reports sync,
   asyncio, or both accurately, without device I/O. Each plugin is registered once in
   the new registry and can be used through every declared execution path.
8. **Given** an installed capability-aware plugin advertised for automatic discovery,
   **When** plugins are discovered, **Then** it is available in the new registry and
   usable by connection name without a manual registration call. Legacy discovery
   continues to populate the existing registry.
9. **Given** different plugins with the same connection name in the two registries,
   **When** that name is resolved, **Then** an explicit ambiguity error occurs before
   either plugin opens a connection; neither silently overrides the other.
10. **Given** a capability-aware plugin with an empty or unsupported capability declaration,
    or missing operations required by its declaration, **When** it is validated for use,
    **Then** an explicit contract error occurs before any connection is opened.

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
  a named error is raised before host execution for top-level calls, before subtask
  execution for subtask calls, and before opening or returning an incompatible
  connection for connection calls. The message names the entry point to use instead.
- The caller cancels `arun` mid-run: cancellation propagates, nothing is recorded.
- A host holds a mix of synchronous and asynchronous connections at cleanup: both kinds
  are closed.
- A connection from a capability-aware plugin declaring both capabilities was opened by a synchronous
  task and is later requested from an async task under the same name: the cached
  connection is returned, nothing is reopened. Cached connections from plugins lacking
  the requested capability raise the same named mismatch error as an uncached request.
- A capability-aware plugin exposes extra methods but does not declare the corresponding
  capability: that execution path remains unavailable. Method presence does not override
  the declaration.
- A legacy plugin exposes async methods as extensions: legacy registration alone still
  provides only synchronous support. Opting into the new contract enables capability-aware use.
- A name exists in both registries: lookup reports ambiguity before opening a connection.
- A capability declaration is invalid or its required operations are missing: fail before
  opening a connection, rather than reporting support that cannot be used.
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
- **FR-011**: A new optional `CapabilityConnectionPlugin` contract MUST support plugins
  declaring synchronous execution, asyncio execution, or both. It MUST expose the
  established `connection` and require working open/close operations for every declared
  capability: `open`/`close` for sync and `aopen`/`aclose` for asyncio. Async operations
  MUST accept the same connection parameters, in the same order, as their synchronous
  counterparts. Existing `ConnectionPlugin` members and signatures MUST NOT change.
- **FR-012**: `Host` MUST provide `aget_connection`, `aopen_connection`,
  `aclose_connection` and `aclose_connections`, mirroring the existing synchronous
  methods. Both execution paths MUST resolve plugins by name across the legacy and
  capability-aware registries and maintain one logical connection per host and name.
  A plugin declaring both capabilities MUST reuse its established connection across
  paths. Storage MUST preserve existing public cache types and synchronous behavior;
  the internal representation is a planning decision.
- **FR-013**: `Host.aget_connection()` on a plugin without asyncio capability MUST raise a
  named error pointing to `get_connection()`; `Host.get_connection()` on a plugin
  without synchronous capability MUST raise the mirror error pointing to
  `aget_connection()`. These checks MUST apply before opening a connection and before
  returning a cached connection; rejection MUST leave an existing cache entry intact.
- **FR-014**: `Host.aclose_connections()` MUST close every open connection on the host,
  awaiting `aclose` on async-capable plugins and calling `close` on synchronous ones.
- **FR-015**: `Nornir.aclose_connections()` MUST run as a task through `arun()` so that
  processors observe it and `on_good`/`on_failed` apply; `async with nr:` MUST close
  the connections of good and failed hosts on exit.
- **FR-016**: Cancelling `Nornir.arun()` MUST cancel every in-flight host, propagate
  the cancellation to the caller, and MUST NOT record a result, update
  `failed_hosts`, or emit `task_completed`.
- **FR-017**: Processors attached to an async run MUST receive the same events and
  arguments as on a synchronous run. Global start MUST precede host events; each host's
  start MUST precede its completion; child events MUST occur within their parent's
  execution; global completion, when emitted, MUST follow host completions. Cross-host
  interleaving is permitted. Failure and cancellation retain their specified rules for
  omitted completion events.
- **FR-018**: A standard-library-only reference async connection plugin (`AsyncEcho`)
  MUST implement `CapabilityConnectionPlugin`, declare asyncio support, and register in
  `CapabilityConnectionPluginRegister` as a test fixture, exercising the complete async connection path in the
  test suite on every supported platform; it MUST NOT ship in the installed package.
- **FR-019**: Documentation MUST include an executed how-to notebook demonstrating
  runner selection, an async task, `arun`, `async with`, and the named errors as real
  output, and a prose how-to page for plugin authors that includes the source of the
  reference fixture and the two rules for async members (`aopen`/`aclose` must not
  block; `aclose` must be safe to call more than once). The plugin-author guide MUST
  explain capability reporting, registration and discovery through the new registry,
  all three capability combinations, and continued support for legacy plugins.
- **FR-020**: No existing public signature, protocol member, default value or
  entry-point name MAY change; the pre-existing test suite MUST pass unmodified except
  for updating the runner-registry assertion and its import in
  `tests/core/test_registered_plugins.py` to include `asyncio` / `AsyncioRunner`.
- **FR-021**: `CapabilityConnectionPluginRegister` MUST register and discover plugins
  implementing the new contract for all three capability combinations. A plugin MUST
  register once in this registry regardless of how many capabilities it supports.
  `ConnectionPluginRegister` and the existing `nornir.plugins.connections` discovery
  group MUST continue accepting legacy plugins without changes to their code or registration.
- **FR-022**: `CapabilityConnectionPlugin` MUST provide a capability-reporting method
  usable before opening a connection and without device I/O. It MUST report a nonempty
  selection of sync and asyncio capabilities. Dispatch MUST honor that declaration;
  legacy registrations MUST be treated as sync-only. Invalid declarations or missing
  required operations MUST produce an explicit contract error before opening a connection.
- **FR-023**: Connection lookup MUST reject a name present in both registries with an
  explicit ambiguity error before opening a connection. Lookup MUST NOT silently select
  one registry based on execution mode or discovery order.

### Key Entities

- **Asyncio runner**: A runner plugin, registered as `asyncio`, that executes a task
  over the selected hosts concurrently on the caller's event loop, bounded by
  `num_workers`. New; joins `serial` and `threaded` as an in-tree runner (approved
  under Constitution principle II).
- **Async entry points on `Nornir`**: `arun`, `aclose_connections`, and async context
  manager support. Existing entity, new members; the synchronous members are unchanged.
- **Coroutine-aware `Task`**: `astart` and `arun` as async twins of `start` and `run`,
  sharing the same result and failure semantics. Existing entity, new members.
- **`CapabilityConnectionPlugin` contract**: The new capability-aware connection plugin
  contract, with capability reporting, the established connection, and operations for
  every declared execution mode. It accepts sync-only, asyncio-only, and dual-capability plugins.
- **`CapabilityConnectionPluginRegister`**: The new registry for all plugins implementing
  the capability-aware contract, independent of their supported execution modes.
- **Legacy connection contract and registry**: `ConnectionPlugin` and
  `ConnectionPluginRegister`, preserved for existing synchronous plugins without migration.
- **Connection capabilities**: Sync, asyncio, or both, reported by the new contract and
  used to validate execution-path requests. Exact method signature and value types belong
  to planning.
- **Async connection methods on `Host`**: `aget_connection`, `aopen_connection`,
  `aclose_connection`, `aclose_connections`, maintaining a per-host connection identity
  keyed by name across execution paths and plugin registries. Existing entity, new members.
- **Named errors**: One error per wrong sync/async combination, each message naming the
  entry point to use instead. New.
- **`AsyncEcho` fixture**: A standard-library-only async connection plugin living in the
  test suite, whose source is included in the plugin-author documentation. New,
  test-only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The complete pre-existing test suite passes once the feature is merged,
  with only the runner-registry assertion and its import updated to include `asyncio` /
  `AsyncioRunner`. Upgrading requires zero code changes for users who do not select the
  `asyncio` runner.
- **SC-002**: During a run over 100 hosts whose task awaits 100 ms of simulated I/O,
  another coroutine sharing the caller's event loop is never starved for more than
  50 ms.
- **SC-003**: A run over 1,000 hosts, each awaiting 100 ms of simulated I/O, with
  `num_workers=1000`, completes in under 2 seconds of wall-clock time, and the number
  of live threads in the process is the same before and after the run.
- **SC-004**: Every wrong sync/async combination listed in the edge cases raises a
  named error at the relevant operation boundary: top-level mismatches before any host
  execution or per-host event; subtask mismatches before the subtask executes or emits
  a subtask event; connection mismatches before opening or returning an incompatible
  connection, including on cache hits. Parent host events may already have occurred
  for subtask and connection calls.
- **SC-005**: A plugin author can implement the capability-aware contract and register
  once in `CapabilityConnectionPluginRegister` to serve every declared execution path.
  Tests demonstrate sync-only, asyncio-only, and dual-capability plugins, including
  cross-path connection reuse for the dual-capability case. Existing legacy plugins
  remain usable without implementing the new contract or changing registration.
- **SC-006**: The how-to notebook executes in the documentation build and its stored
  output matches the run on every documentation build.
- **SC-007**: Registration and discovery tests demonstrate both registries coexisting:
  legacy names resolve through the synchronous path, capability-aware names resolve
  through each declared path, duplicate cross-registry names fail explicitly, and invalid
  capability declarations fail before connection-opening operations are invoked.

## Clarifications

### Session 2026-09-13

- Q: May registering `asyncio` update the existing exact runner-registry test? → A: Yes;
  the assertion and its import may include `asyncio` / `AsyncioRunner`. Other existing
  tests must pass unmodified.
- Q: When must mismatch errors be raised? → A: Before host execution for top-level
  calls, before subtask execution for subtask calls, and before opening or returning
  an incompatible connection for connection calls, including cached connections.
- Q: Is the successor registry specific to async plugins? → A: No. Use
  `CapabilityConnectionPlugin` and `CapabilityConnectionPluginRegister` for plugins
  supporting sync, asyncio, or both, with a method reporting capabilities. Preserve the
  existing protocol and registry as the legacy compatibility path.

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
- New plugins satisfy the capability-aware contract structurally, consistent with the
  existing plugin model, but supported execution modes come from the capability method,
  not from method-presence heuristics. Legacy registrations are synchronous-only.
- Default namespace policy: any name present in both registries is ambiguous, even if
  both entries refer to the same class. Authors opting into the new registry remove the
  old registration for that name; dual-capability plugins need only the new registration.
- The capability method's exact signature and result type, typed operation interfaces,
  discovery entry-point name for the new registry, error class names, and internal
  storage design are settled during planning. They must satisfy FR-011–FR-013 and
  FR-020–FR-023 without weakening existing public types or signatures.
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
- Renaming, removing, or requiring deprecation warnings for the legacy connection
  protocol and registry; existing plugins need not adopt the new contract in this release.
- A major-version upgrade guide: the release is additive and nothing breaks.
