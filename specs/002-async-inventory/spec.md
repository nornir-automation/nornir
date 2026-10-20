# Feature Specification: Async Inventory

**Feature Branch**: `dga/feat-async-inventory-o5wf5`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Async inventory proposal from nornir-automation/nornir#1087, refined in an idea
grilling session on 2026-10-16. Add an opt-in asynchronous way to build a `Nornir` object,
`await AInitNornir(...)`, for applications that already run an event loop, and a
capability-aware inventory plugin contract so that inventory sources with async API clients
(Infrahub, NetBox, Nautobot) have a first-class place to plug in. Async transform functions
ship in the same release. Three decisions differ from the proposal as written in #1087:
inventory plugins follow the capability-aware pattern adopted for connections in spec 001
instead of an async-only registry; `AInitNornir` runs a synchronous plugin's `load()` in a
worker thread instead of on the event loop; async transform functions ship in the first
version with their own registry. Depends on `specs/001-asyncio-runner`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build Nornir from an async application with any existing inventory plugin (Priority: P1)

An application developer whose program already runs an event loop (a web service, a bot,
an async test suite, a workflow tool such as NornFlow) replaces `InitNornir(...)` with
`await AInitNornir(...)` at startup. The configuration file, the keyword arguments and the
inventory plugin stay exactly as they are; the plugin may be `SimpleInventory` or any
existing third-party plugin that only implements the synchronous `load()`. The developer
gets back the same `Nornir` object `InitNornir` would have built, and the application's
event loop keeps serving other work for the whole time the inventory loads.

**Why this priority**: No async inventory plugin exists yet, so this is the only story
that delivers value on the day of release. It was the one request made by the only
outside reviewer of #1087: existing plugins must work from an async application "from
day one".

**Independent Test**: Start an event loop, run a background coroutine that counts ticks,
call `await AInitNornir(...)` with a synchronous test plugin whose `load()` waits on an
external signal, and check that the counter keeps advancing while `load()` waits and that
the returned inventory equals the one `InitNornir` builds from the same configuration.

**Acceptance Scenarios**:

1. **Given** an application with a running event loop and a configuration that names
   `SimpleInventory`, **When** it calls `await AInitNornir(config_file=...)`, **Then** it
   receives a `Nornir` object whose hosts, groups and defaults equal those `InitNornir`
   builds from the same file.
2. **Given** a synchronous inventory plugin whose `load()` takes several seconds,
   **When** an application calls `await AInitNornir(...)`, **Then** other coroutines on the
   application's event loop keep running during the whole load.
3. **Given** a synchronous inventory plugin whose `load()` calls `asyncio.run()`
   internally, **When** an application with a running event loop calls
   `await AInitNornir(...)`, **Then** the load succeeds.
4. **Given** an application that today calls `InitNornir(...)` with keyword arguments,
   **When** it calls `await AInitNornir(...)` with the same arguments, **Then** no argument
   is rejected or interpreted differently.

---

### User Story 2 - Ship an inventory plugin that supports async loading (Priority: P2)

An inventory plugin author whose source has an async API client implements `aload()` on a
class that follows the new `CapabilityInventoryPlugin` contract, declares which capabilities
it supports (synchronous, asyncio, or both), and registers the class once. Users select it
by name in `inventory.plugin`, as they do today. `AInitNornir` awaits `aload()`;
`InitNornir` calls `load()` when the plugin supports synchronous loading and raises a
named error that points to `AInitNornir` when it does not.

**Why this priority**: This is what lets async-native inventory sources stop working
around the event loop. It depends on Story 1, because `aload()` has no caller without
`AInitNornir`.

**Independent Test**: Register a test plugin that supports both capabilities and records
which method was called; check that `AInitNornir` calls only `aload()` and `InitNornir`
calls only `load()`. Register an asyncio-only plugin and check that `InitNornir` raises
the named error before any loading method is called.

**Acceptance Scenarios**:

1. **Given** a plugin class that declares both capabilities and is registered once under
   the capability inventory entry-point group, **When** a user calls `AInitNornir` with its
   name, **Then** `aload()` is awaited and `load()` is not called.
2. **Given** the same plugin, **When** a user calls `InitNornir` with its name, **Then**
   `load()` is called and `aload()` is not.
3. **Given** a plugin that declares only the asyncio capability, **When** a user calls
   `InitNornir` with its name, **Then** `InventoryPluginNotSyncError` is raised before any
   loading method is called, and its message names `AInitNornir` as the fix.
4. **Given** a plugin that declares only the synchronous capability, **When** a user calls
   `AInitNornir` with its name, **Then** `load()` runs in a worker thread, as for a legacy
   plugin in Story 1.

---

### User Story 3 - Enrich hosts from an async source with an async transform function (Priority: P3)

A user who fills in host data from a secrets store or an IPAM with an async client writes
the transform function with `async def` and registers it in the async transform function
registry. `AInitNornir` awaits it once per host, in inventory order, one host at a time.
`InitNornir` refuses such a transform with a named error instead of skipping it silently,
which is what happens today.

**Why this priority**: The main reason for async transforms is a source that only offers an
async client; a synchronous client already leaves the loop free under Story 1, because
`AInitNornir` runs synchronous transforms in the worker thread. It is independent of
Story 2.

**Independent Test**: Register an async transform that records each host's name with a
start and end marker; check that `AInitNornir` produces one record per host, in inventory
order, with no overlap between records. Configure the same transform with `InitNornir`
and check that the named error is raised and the inventory plugin is never called.

**Acceptance Scenarios**:

1. **Given** an async transform function registered under the async transform function
   entry-point group, **When** `AInitNornir` loads an inventory of N hosts, **Then** the
   transform is awaited exactly N times, in inventory order, and each call finishes before
   the next one starts.
2. **Given** a synchronous transform function, **When** `AInitNornir` loads the inventory,
   **Then** the transform runs in a worker thread and other coroutines on the loop keep
   running.
3. **Given** an async transform function, **When** a user calls `InitNornir`, **Then**
   `TransformFunctionNotSyncError` is raised before the inventory plugin is called.
4. **Given** an async transform function that raises on the third host, **When**
   `AInitNornir` loads the inventory, **Then** the exception propagates to the caller and
   no `Nornir` object is returned.

---

### Edge Cases

- **A transform raises on a host**: the exception propagates and no `Nornir` object is
  returned, for both entry points. This is the current `InitNornir` behaviour.
- **The configured name is not registered in any inventory registry**: `PluginNotRegistered`,
  unchanged from today.
- **The same name is registered in the legacy inventory registry and the capability
  inventory registry**, or in the synchronous and async transform function registries: both
  entry points raise an explicit ambiguity error before any plugin or transform code runs.
  Neither registry is chosen silently.
- **A capability inventory plugin or async transform uses a name already taken by a legacy
  plugin of another kind** (for example `threaded`, the threaded runner): this is also
  reported as ambiguous. The existing inventory, transform, runner and connection
  registries share one set of names today, so the legacy side of the check sees all of
  them. The error message names both registries; renaming the new plugin is the fix.
- **A capability plugin's declaration is invalid** (empty, contains an unknown value, cannot
  be read) **or it lacks the method for a capability it declares**: an explicit contract
  error is raised before the plugin loads.
- **A plugin declares both capabilities**: `AInitNornir` calls `aload()` only; `InitNornir`
  calls `load()` only.
- **The application cancels `AInitNornir` during `aload()` or an async transform**:
  cancellation reaches the plugin or transform, `CancelledError` propagates, and no `Nornir`
  object is returned.
- **The application cancels `AInitNornir` while a synchronous `load()` or transform runs in
  the worker thread**: `CancelledError` is raised to the caller promptly and no `Nornir`
  object is returned. The thread cannot be stopped; it keeps running until `load()` or the
  transform returns, and its result is discarded. A plugin that hangs without a timeout can
  delay the application's shutdown. This is documented, not worked around.
- **A transform defined with `async def` is registered in the synchronous transform
  registry**: it is treated as an async transform by both entry points (awaited by
  `AInitNornir`, refused by `InitNornir`). A plain function registered in the async
  transform registry runs in the worker thread under `AInitNornir` and normally under
  `InitNornir`.
- **The inventory is empty**: `AInitNornir` returns a `Nornir` object with no hosts, as
  `InitNornir` does; a configured transform is never called.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `AInitNornir` MUST be awaitable from a running event loop and MUST return the
  same type of object as `InitNornir`.
- **FR-002**: `AInitNornir` MUST accept the same arguments as `InitNornir`, with the same
  names, defaults and meaning, and MUST read configuration, configure logging and build the
  runner exactly as `InitNornir` does. The two entry points MUST differ only in how the
  inventory is loaded.
- **FR-003**: For a legacy inventory plugin, or a capability inventory plugin that declares
  only the synchronous capability, `AInitNornir` MUST call `load()` in a worker thread and
  MUST NOT call it on the event loop.
- **FR-004**: For a capability inventory plugin that declares the asyncio capability,
  `AInitNornir` MUST await `aload()` and MUST NOT call `load()`.
- **FR-005**: `AInitNornir` MUST NOT create, run or close an event loop of its own.
- **FR-006**: `InitNornir` MUST behave exactly as today for legacy inventory plugins and
  synchronous transform functions.
- **FR-007**: `InitNornir` MUST call `load()` for a capability inventory plugin that declares
  the synchronous capability, and MUST raise `InventoryPluginNotSyncError` before calling
  any loading method of a plugin that declares only the asyncio capability. The message MUST name
  the plugin and say that `await AInitNornir(...)` is the entry point to use.
- **FR-008**: A new optional `CapabilityInventoryPlugin` contract MUST let a plugin declare a
  nonempty selection of the synchronous and asyncio capabilities, and implement `load()`,
  `aload()` or both to match. The declaration MUST be readable from the configured plugin
  instance before the plugin loads; constructing the plugin and reading its declaration
  MUST NOT perform I/O. `aload()` MUST return the same kind of inventory object as `load()`.
- **FR-009**: A new `CapabilityInventoryPluginRegister` MUST discover capability inventory
  plugins through its own entry-point group, for all three capability combinations. A plugin
  MUST register once regardless of how many capabilities it declares.
  `InventoryPlugin`, `InventoryPluginRegister` and the `nornir.plugins.inventory` group MUST
  keep their exact types, contents and behaviour.
- **FR-010**: A new optional `AsyncTransformFunction` contract and a new
  `AsyncTransformFunctionRegister`, discovered through its own entry-point group, MUST accept
  transform functions defined with `async def`. `TransformFunction`,
  `TransformFunctionRegister` and the `nornir.plugins.transform_function` group MUST keep
  their exact types, contents and behaviour.
- **FR-011**: `AInitNornir` MUST await a transform function defined with `async def`,
  whichever transform registry it was found in, once per host, in
  inventory order, one host at a time, passing the configured transform options exactly as
  a synchronous transform receives them today.
- **FR-012**: `AInitNornir` MUST run a synchronous transform function in a worker thread,
  not on the event loop.
- **FR-013**: `InitNornir` MUST raise `TransformFunctionNotSyncError` before calling the
  inventory plugin when the configured transform function is defined with `async def`,
  whichever transform registry it was found in.
  The message MUST name the transform and say that `await AInitNornir(...)` is the entry
  point to use. Today `InitNornir` skips such a transform with only a "coroutine was never
  awaited" warning and leaves the hosts unchanged; raising instead is a bug fix, shipped in
  the MINOR release without a deprecation period, recorded as a fix in `CHANGELOG.rst` and
  called out in the pull request.
- **FR-014**: A name present in both the legacy and the capability inventory registries, or
  in both the synchronous and async transform function registries, MUST be rejected by both
  entry points with an explicit ambiguity error before any plugin or transform code runs.
  Because the legacy registries currently share one set of names, this includes a name used
  by a legacy runner, connection, inventory or transform plugin.
- **FR-015**: An invalid capability declaration, or a missing method for a declared
  capability, MUST raise an explicit contract error before the plugin loads.
- **FR-016**: `InventoryPluginNotSyncError` and `TransformFunctionNotSyncError` MUST be
  subclasses of `SyncAsyncMismatchError`, so that callers can catch every sync/async
  mismatch with one `except` clause.
- **FR-017**: When the caller cancels `AInitNornir`, `CancelledError` MUST propagate to the
  caller without waiting for a synchronous `load()` or transform running in a worker
  thread, and no `Nornir` object MUST be returned.
- **FR-018**: Tracebacks raised from `aload()`, from a synchronous `load()` run in the
  worker thread, and from an async transform MUST point at the plugin's or transform's own
  code. Users MUST be able to step into each of them with `pdb`; this part is checked by
  hand before the pull request, because an interactive debugger cannot be driven reliably
  from the test suite.
- **FR-019**: The documentation MUST include an executed how-to for `AInitNornir`, a guide
  for plugin authors on the capability inventory contract and the async transform contract,
  a note on cancellation of synchronous plugins and the need for network timeouts, and a
  `CHANGELOG.rst` entry.

### Key Entities

- **`AInitNornir`** (new): asynchronous entry point that builds a `Nornir` object. Same
  arguments and return type as `InitNornir`.
- **`aload_inventory`** (new): asynchronous counterpart of `load_inventory`; resolves the
  configured plugin and transform and loads the inventory without blocking the loop.
- **`CapabilityInventoryPlugin`** (new): inventory plugin contract with a capability
  declaration and `load()`, `aload()` or both.
- **`CapabilityInventoryPluginRegister`** (new): registry for capability inventory plugins;
  entry-point group `nornir.plugins.capability_inventory`.
- **`AsyncTransformFunction`** (new): contract for a transform function defined with
  `async def`; same arguments as `TransformFunction`.
- **`AsyncTransformFunctionRegister`** (new): registry for async transform functions;
  entry-point group `nornir.plugins.async_transform_function`.
- **`InventoryPluginNotSyncError`**, **`TransformFunctionNotSyncError`** (new): raised by
  `InitNornir` for an asyncio-only plugin or an async transform; subclasses of
  `SyncAsyncMismatchError`.
- **`InitNornir`**, **`load_inventory`**, **`InventoryPlugin`**, **`InventoryPluginRegister`**,
  **`TransformFunction`**, **`TransformFunctionRegister`**, **`Inventory`** (existing):
  unchanged in signature and type. `InitNornir` and `load_inventory` behave as today for
  legacy plugins and synchronous transforms, and gain the behaviour in FR-007, FR-013,
  FR-014 and FR-015.
- **`SyncAsyncMismatchError`**, capability declaration validation (existing, from spec 001):
  reused.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An application that uses any existing inventory plugin, `SimpleInventory`
  included, moves from `InitNornir` to `AInitNornir` by changing only the init call: zero
  changes to the configuration file, the arguments or the plugin.
- **SC-002**: For the same configuration, `AInitNornir` and `InitNornir` produce equal
  inventories (same hosts, groups, defaults and transform results) in 100% of the
  configurations covered by the existing inventory tests.
- **SC-003**: While an inventory loads through `AInitNornir`, other work on the
  application's event loop keeps making progress for every combination of synchronous or
  asyncio plugin and synchronous or async transform (4 of 4 combinations).
- **SC-004**: 100% of the existing tests pass without modification, and the legacy inventory
  and transform function contracts and registries keep their exact types and contents.
- **SC-005**: Every unsupported combination (an asyncio-only plugin under `InitNornir`, an
  async transform under `InitNornir`, a name registered in two registries, an invalid
  capability declaration) fails before any loading method or transform runs, with a message
  that names the entry point or change that fixes it.
- **SC-006**: A plugin author makes one class available to both entry points with exactly
  one entry-point registration.
- **SC-007**: When an application cancels `AInitNornir` while a synchronous plugin is
  loading, control returns to the application without waiting for the plugin to finish.

## Clarifications

### Session 2026-10-16

- Q: `InitNornir` currently skips an `async def` transform with only a "coroutine was never
  awaited" warning. Can raising `TransformFunctionNotSyncError` instead ship in a MINOR
  release, or does it need a deprecation period? → A: Ship it in the MINOR release as a bug
  fix, without a deprecation period. The transform never ran, so no working configuration
  depends on the current behaviour. The change is recorded as a fix in `CHANGELOG.rst` and
  called out in the pull request (FR-013).

## Assumptions

- Reading the configuration file and configuring logging stay on the event loop, as in
  `InitNornir`: they are small, local operations.
- The worker thread comes from the running loop's default executor; the application
  controls its size.
- A synchronous plugin's `load()` runs alone in its worker thread, with no concurrent calls,
  so it needs no thread safety beyond what it has today. A plugin that depends on
  thread-local state set up by the caller will not see that state.
- Async transform functions are awaited one host at a time. Running them concurrently is a
  separate optimisation with its own failure semantics.
- The ambiguity and contract errors follow the behaviour of the connection errors from spec
  001 (`ConnectionPluginAmbiguousError`, `ConnectionPluginContractError`); whether they are
  reused, generalised or mirrored by inventory-specific classes is decided during planning.
- This feature depends on `specs/001-asyncio-runner` for `SyncAsyncMismatchError` and the
  capability declaration validation, and ships in the same MINOR release or a later one.
- `AInitNornir` is independent of the runner: it works with `ThreadedRunner`,
  `SerialRunner` and the asyncio runner.
- #1087 receives a comment that records the three decisions that differ from the proposal.

### Out of Scope

- An async `SimpleInventory`: it reads a local file, and the standard library has no async
  file I/O.
- An inventory reload or refresh API.
- Running transform functions for several hosts at the same time.
- Async `Inventory.filter`, `Host` access or `ConnectionOptions`: these are in-memory
  operations.
- Async processors: covered by #1090.
- A Nornir-managed thread or daemon thread to stop a hung synchronous plugin on
  cancellation.
