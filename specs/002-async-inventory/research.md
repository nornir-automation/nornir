# Research: Async Inventory

**Feature**: 002-async-inventory | **Spec**: [spec.md](spec.md) | **Date**: 2026-10-16

Each section records a decision, why it was chosen, and the alternatives considered. The
user-facing decisions (capability pattern, worker thread, async transforms in v1, names,
FR-013 as a fix) were settled before the spec and are not reopened here.

## R1. How the capability declaration is read for inventory plugins

**Decision**: `CapabilityInventoryPlugin.get_capabilities()` is an instance method, as in
`CapabilityConnectionPlugin`. The core constructs the plugin with `inventory.options`, reads
the declaration, validates it, and only then calls `load()` or `aload()`. The contract states
that constructing the plugin and reading its declaration perform no I/O.

**Rationale**: One reporting shape across the two capability contracts; a plugin author who
writes both learns one rule. Inventory plugins take constructor options (connection
plugins do not), and a plugin may legitimately report capabilities that depend on them (for
example, `asyncio` only when an async client library is importable).

**Consequence for the spec**: FR-007 and SC-005 originally said "before the plugin is
instantiated" and "before any plugin code runs". The constructor and `get_capabilities()`
are plugin code, so the wording was changed to "before any loading method is called" and
"before any loading method or transform runs". The registry ambiguity check still runs
before construction.

**Alternatives considered**:
- A `classmethod` or class attribute, readable without construction. Rejected: it diverges
  from the connection contract and cannot depend on options.
- Inferring capabilities from which methods exist (`load` / `aload`). Rejected: the
  connection contract chose an explicit declaration so a dual class can deliberately expose
  only one mode, and the same reasoning holds here.

## R2. Reusing the capability validation from spec 001

**Decision**: Do not generalise `_validate_capability_plugin` in `nornir/core/inventory.py`.
Add a separate private `_validate_capability_inventory_plugin(name, plugin)` beside the new
contract in `nornir/core/plugins/inventory.py`. It applies the same rules in the same order:

1. `get_capabilities` is accessible, callable and not a coroutine function;
2. calling it succeeds (the original exception is chained on failure);
3. the result is a `frozenset` equal to `{"sync"}`, `{"asyncio"}` or `{"sync", "asyncio"}`;
4. `sync` requires a callable, non-coroutine `load`; `asyncio` requires a coroutine-function
   `aload`; dual requires both.

**Rationale**: The connection helper raises connection-specific errors and checks
connection-specific operations (`open`/`close`/`aopen`/`aclose`); after removing those,
the shared part is about fifteen lines. Extracting a generic helper parameterised by an
error factory and an operation guard would touch spec 001's code path, which has already
passed analysis, for little gain. Duplication is limited to the declaration check and is
covered by parallel tests.

**Alternatives considered**: A shared `_read_capability_declaration(owner, error_factory)`
helper in `nornir/core/plugins/register.py`. Reasonable as a follow-up once both specs have
merged; not worth reopening spec 001 for now.

## R3. Capability type

**Decision**: Add `InventoryCapability = Literal["sync", "asyncio"]` in
`nornir/core/plugins/inventory.py`.

**Rationale**: Mirrors `ConnectionCapability` without making the inventory contract import
from the connections module. The two aliases are the same type for mypy, so code that
handles both is not affected.

**Alternatives considered**: Reusing `ConnectionCapability` (misleading name in inventory
signatures); renaming it to a shared `PluginCapability` (changes spec 001's public names).

## R4. Running synchronous work off the event loop

**Decision**: `await asyncio.to_thread(fn)` for the synchronous parts of `aload_inventory`.
The synchronous parts are grouped so that one thread call is made per phase:

| Plugin | Transform | Thread calls |
|---|---|---|
| sync or legacy | none or sync | one: `load()` then every sync transform |
| sync or legacy | async | one: `load()`; transforms awaited on the loop |
| asyncio | sync | one: every sync transform, after `await aload()` |
| asyncio | none or async | none |

**Rationale**:
- `asyncio.to_thread` is in the standard library on every supported Python (3.10–3.14), so
  no dependency is added (Principle II).
- It uses the running loop's default executor; it neither creates nor drives a loop (FR-005).
- It copies the caller's `contextvars` context into the thread, so context-local state set by
  the application (for example a request id used in logging) is visible to `load()`.
- A worker thread has no running event loop, so a synchronous plugin that calls
  `asyncio.run()` internally succeeds (acceptance scenario 1.3).
- `pdb.set_trace()` works in the worker thread, and exceptions propagate to the awaiting
  coroutine with their original traceback (FR-018).

**Construction**: a legacy plugin is also constructed in the worker thread, because legacy
constructors were never required to be free of I/O. A capability plugin is constructed on
the loop, because its declaration must be read first and its contract forbids I/O in the
constructor.

**Cancellation (FR-017)**: when the awaiting task is cancelled, `to_thread`'s future is
cancelled and `CancelledError` is raised in the caller immediately; the running thread
cannot be interrupted and its result is discarded. No `asyncio.shield` is used, so the
Python 3.14 shield warning fixed in commit 777cd55 does not apply.

**Alternatives considered**:
- `loop.run_in_executor(None, ...)`: equivalent but does not copy `contextvars`.
- A Nornir-owned `ThreadPoolExecutor` or daemon thread: rejected in the grilling session;
  Nornir would manage concurrency outside its runner, and shutdown semantics would differ
  from the application's own executor.

## R5. Classifying transform functions

**Decision**: Both entry points classify the resolved transform with
`inspect.iscoroutinefunction`, applied to the transform and to its class's `__call__`,
regardless of which registry it was found in.
`InitNornir` raises `TransformFunctionNotSyncError` for a coroutine function; `AInitNornir`
awaits a coroutine function and runs any other callable in the worker thread. The two
registries exist for discovery and typing, not for dispatch.

**Rationale**: This mirrors spec 001, where the runner classifies tasks by
`inspect.iscoroutinefunction`. It turns the case "an `async def` transform registered in
the old group", which is what users write today when they try this, into working code under
`AInitNornir` and a named error under `InitNornir`, instead of a third error class.

**Callable objects**: `inspect.iscoroutinefunction` is False for an instance whose class
defines `async def __call__`, although such an instance satisfies `AsyncTransformFunction`.
The class's `__call__` is therefore checked as well, so these objects are awaited by
`AInitNornir` and refused by `InitNornir` like `async def` functions.

**Alternatives considered**: Dispatch by registry, with a `TransformFunctionContractError`
for a mismatch between registry and definition. Rejected: more errors for no user benefit.

## R6. Registry lookup and ambiguity

**Decision**:
- Inventory: if the name is in both `InventoryPluginRegister.available` and
  `CapabilityInventoryPluginRegister.available`, raise `InventoryPluginAmbiguousError`;
  otherwise use the capability registry if it has the name, the legacy registry if it has
  the name, and raise `PluginNotRegistered` if neither does.
- Transform: the same rule with `TransformFunctionRegister`,
  `AsyncTransformFunctionRegister` and `TransformFunctionAmbiguousError`.
- Both entry points call `auto_register()` on both registries of each kind before lookup.
- Both lookups happen before the plugin is constructed (FR-013, FR-014).

**Finding: the legacy registries share one dictionary.** `PluginRegister.available` is a
class attribute, and `register()` mutates it in place, so `InventoryPluginRegister`,
`TransformFunctionRegister`, `RunnersPluginRegister` and `ConnectionPluginRegister` all
read and write the same `dict` until `deregister_all()` is called on one of them. Verified
on this branch: after auto-registration, `ConnectionPluginRegister.available` lists
`SimpleInventory`, `asyncio`, `serial` and `threaded`. Spec 001 works around this by
assigning `CapabilityConnectionPluginRegister.available = {}`.

Consequences for this feature:
- Each new register MUST be given its own dictionary, as spec 001 does.
- The ambiguity check against a legacy register can report a false collision with a plugin
  of another kind; for example, a capability inventory plugin named `threaded` collides
  with the threaded runner. The error message names both registries, so the cause is
  visible, and renaming is the fix.
- Fixing `PluginRegister` itself (per-instance dictionary) changes what the legacy
  registries return today — `InventoryPluginRegister.get_plugin("threaded")` currently
  returns `ThreadedRunner` — so it is out of scope here. A separate bug issue is recommended.

**Alternatives considered**: Fixing `PluginRegister` in this feature. Rejected: it is an
existing behaviour of the public registries, unrelated to async, and needs its own
regression test and changelog entry.

## R7. Error classes

**Decision**: Five new classes in `nornir/core/exceptions.py`:

| Class | Base | Raised when |
|---|---|---|
| `InventoryPluginNotSyncError` | `SyncAsyncMismatchError` | `InitNornir` with a plugin that declares only `asyncio` |
| `TransformFunctionNotSyncError` | `SyncAsyncMismatchError` | `InitNornir` with an `async def` transform |
| `InventoryPluginAmbiguousError` | `Exception` | name in both inventory registries |
| `InventoryPluginContractError` | `Exception` | invalid declaration or missing declared method |
| `TransformFunctionAmbiguousError` | `Exception` | name in both transform registries |

No transform contract error is needed because of R5.

**Rationale**: Spec 001's `ConnectionPluginAmbiguousError` and
`ConnectionPluginContractError` take a `connection_name` and say "Connection plugin" in
their message, so reusing them for inventory would produce misleading messages. A common
base class would rename spec 001's public classes. Separate classes keep the same shape
(name attribute, `reason` for contract errors) and the same base classes, so callers catch
them the same way.

**Alternatives considered**: A shared `PluginAmbiguousError(kind, name)` base. Possible later,
once spec 001 has shipped and the pattern has three users.

## R8. Sharing code between `InitNornir` and `AInitNornir`

**Decision**: Extract a private `_prepare(config_file, dry_run, **sections) -> tuple[Config,
GlobalState]` that registers connection plugins, builds the `Config` and configures logging.
`InitNornir` returns `Nornir(inventory=load_inventory(config), runner=load_runner(config),
...)`; `AInitNornir` does the same with `await aload_inventory(config)`. Plugin and transform
resolution (R6) and validation (R2) are private helpers used by both `load_inventory` and
`aload_inventory`.

**Rationale**: FR-002 requires the two entry points to differ only in how the inventory is
loaded. Order of operations is kept as today: configuration and logging first, then the
inventory, then the runner.

**Note**: Reading the configuration file and configuring logging stay on the event loop
(spec assumption); they are small local operations.

## R9. Documentation

**Decision**:
- `docs/howto/async_inventory.ipynb`: executed notebook. Jupyter runs an event loop, so cells
  use top-level `await AInitNornir(...)`. It covers `SimpleInventory` under `AInitNornir`, a
  small capability inventory plugin registered in-process, and an async transform.
- `docs/howto/writing_capability_inventory_plugins.rst`: guide for plugin authors, alongside
  the existing `writing_capability_connection_plugins.rst`. It covers the contract, the
  entry-point groups, the no-I/O constructor rule, async transforms, and the cancellation
  note with network timeouts.
- `CHANGELOG.rst`: one feature entry (with #1087) and one fix entry for FR-013.
- `docs/api/`: no new module is added, so `make docs` should not change tracked files; it is
  run anyway and anything it regenerates is committed.

## R10. Tests

**Decision**: One test module per user story — `tests/core/test_async_inventory.py`
(US1), `tests/core/test_capability_inventory.py` (US2), `tests/core/test_async_transforms.py`
(US3) — with shared test plugins in `tests/core/inventory_plugins.py` and a registry fixture in
`tests/core/conftest.py`, applied with a module-level `pytestmark` in each new test module.
Existing tests in `tests/core/test_InitNornir.py` stay unchanged as the FR-006 regression.
Test plugins are registered in-process and the fixture snapshots and restores all four
registries, as `isolated_connection_registries` does in `test_capability_plugins.py`. The
fixture never calls `deregister_all()` on a legacy register, because that would detach it
from the shared dictionary (R6).

- **Loop stays free (SC-003)**: a plugin's `load()` waits on a `threading.Event`; a
  coroutine on the loop sets the event after observing that it was scheduled. If `load()`
  ran on the loop the test would hang, so a timeout on the test turns that into a failure.
- **Order and overlap (FR-011)**: the async transform appends `("start", name)` and
  `("end", name)` around an `await asyncio.sleep(0)`.
- **Cancellation (FR-017)**: cancel the `AInitNornir` task while `load()` waits on an event,
  assert `CancelledError` within a short timeout, then set the event so the thread exits.
- **Entry-point discovery (SC-006)**: one test uses a fake entry point (monkeypatched
  `importlib.metadata.entry_points`) to check that one registration in
  `nornir.plugins.capability_inventory` serves both entry points.

All tests run on the full Python and OS matrix (Principle IV); none is platform-specific.
