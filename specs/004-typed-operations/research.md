# Research: Operations, Typed Actions Across Vendors

**Feature**: 004-typed-operations | **Updated**: 2026-10-25 | [Plan](plan.md)

Research covers the task execution path (`nornir/core/task.py`: `Task._start_steps`,
`Task.astart`, `Task._acall`, `Task._finish`, `Task.copy`), the run objects of spec 003
(`nornir/core/run.py`: `RunContext.step_host`, `RunHandle`, `RunStream`,
`AsyncRunHandle`, `AsyncRunStream`), the entry points of `Nornir` (`nornir/core/__init__.py`:
`_sync_streaming_runner`, `_async_streaming_runner`, `_new_run`), the runners
(`nornir/plugins/runners/__init__.py`, which give each host `task.copy()`), the plugin
registry (`nornir/core/plugins/register.py`) and the configuration
(`nornir/core/configuration.py`). Two typing questions were checked with mypy 2.3.1 under
`--strict --python-version 3.10` and at runtime on CPython 3.10, 3.12 and 3.14. Each entry
records the decision, the reason, and the alternatives that were rejected.

## R1. A generic `Result` without a runtime dependency (FR-021)

- **Decision:** Make `Result`, `RunStream`, `RunHandle`, `AsyncRunStream` and
  `AsyncRunHandle` generic over one type variable whose default is `Any`. The default is
  declared only in the branch the type checker reads:

  ```python
  if TYPE_CHECKING:
      from typing_extensions import TypeVar
      T = TypeVar("T", default=Any)
  else:
      from typing import TypeVar
      T = TypeVar("T")
  ```

  `RunEvent` becomes `PartialResult | Result[T]` where it is used in a generic position.
  `AggregatedResult` and `MultiResult` stay untyped (`Result[Any]`).
- **Rationale:** A probe module defined `Result(Generic[T])` this way, and a downstream module
  annotated `-> Result` and `RunStream` with no parameter. Under `mypy --strict` (which
  includes `disallow_any_generics`) the bare names were accepted and revealed as
  `Result[Any]`, while `RunStream[Out]` revealed `res.result.config` as `str`. At runtime,
  the module imported and `Result[int](...)` worked on 3.10, 3.12 and 3.14, with no
  `typing_extensions` import outside `TYPE_CHECKING`. A downstream project that runs mypy
  always has `typing_extensions`, because mypy depends on it and ships its stubs. FR-021's
  preferred path works, so the fallback result class is not needed.
- **Alternatives rejected:**
  - A plain `TypeVar` with no default: every bare `Result` in a strict downstream project
    fails with "Missing type parameters". That is a typing break (Principle VI).
  - `typing_extensions` as a runtime dependency: forbidden by FR-021 and Principle II.
  - A new `OperationResult` class: only needed if the default failed; it would split the
    result types that processors and `print_result` handle.

## R2. Typing `run_operation` from the Operation class (FR-001, FR-006, FR-008)

- **Decision:** `Operation` is `Generic[InT, OutT]`. `run_operation` has two overloads:
  - `(operation: type[Operation[InT, OutT]], params: InT | Mapping[str, Any] | Callable[[Host], InT] | None = None, ...) -> RunStream[OutT]`
  - `(operation: str, params: Any = None, ...) -> RunStream[Any]`

  `submit_operation`, `arun_operation` and `asubmit_operation` follow the same pattern.
- **Rationale:** The probe showed that mypy infers `RunStream[GetConfigOutput]` from
  `GetConfig` for a static instance, a mapping and a lambda. It rejects
  `lambda h: 3` with "Incompatible return value type (got int, expected GetConfigInput)",
  and the string overload gives `RunStream[Any]`.
- **Alternatives rejected:** an instance of the Operation (`GetConfig()`) as the first
  argument: it adds an object with no state, and the class is what the registry stores.

## R3. Reading the models from the class (FR-009, FR-018)

- **Decision:** `Operation.__init_subclass__` reads the two type arguments from
  `__orig_bases__` with `typing.get_args` and stores them as `input_model` and
  `output_model` class attributes. A subclass that defines `name` is registered as a
  contract. A subclass without `name` is an intermediate base and is not registered. A
  subclass whose type arguments are not classes (a `TypeVar`, or a string forward
  reference) raises `TypeError` when it is defined.
- **Rationale:** The probe read `GetConfigInput` and `GetConfigOutput` back on 3.10 and 3.14,
  including with `from __future__ import annotations`, because base-class expressions are
  always evaluated.
- **Alternatives rejected:** declaring `input_model = ...` and `output_model = ...`
  explicitly: it repeats the type arguments and lets the two drift apart.

## R4. Where dispatch happens: a `Task` subclass, zero extra frames (FR-004, FR-022, FR-024)

- **Decision:** Add a private `_OperationTask(Task)` in `nornir/core/operations.py`.
  `Task` gains two private hooks:
  - `_resolve_call(host, asynchronous) -> None`, called inside the existing `try` of
    `_start_steps` and `_acall`, just before the existing `self.task(self, **self.params)`
    line, which stays unchanged. The base does nothing. (As implemented: the hook sets
    `self.task` and `self.params` rather than returning them, so the call line is not
    touched; `asynchronous` tells which path is running.)
  - `_check_result(result: Result) -> Result`, called in `_finish` for the top-level task
    only, before the result is recorded. The base returns `result` unchanged.

  `_OperationTask` overrides `copy()` to return an `_OperationTask`, and overrides the two
  hooks:
  - `_resolve_call` selects the registration for `(name, host.platform, connection)`,
    checks the task kind against the path (synchronous or asynchronous), builds the
    per-host input when `params` is a callable, and sets `self.task` and `self.params` so
    that processors see the implementation;
  - `_check_result` checks `result.result` against the output model unless the result
    failed.

  Every error is raised inside the `try`, so the existing `except Exception` turns it into a
  failed `Result` for that host only.
- **Rationale:** The runners already hand each host `task.copy()` and drive it through
  `RunContext.step_host` / `astart_host`. A subclass reuses that path completely: deadlines,
  cancellation, partial results, processors and dry-run are not forked (FR-024). The
  implementation is still called from the same line of `Task`, so a traceback shows the
  same frames as a plain `nr.run` (FR-022).
- **Alternatives rejected:**
  - A dispatcher function passed as the task (`_dispatch(task, **kw)` that calls the
    implementation): adds one frame to every traceback and every `pdb` step, contrary to
    FR-022, and processors would see the dispatcher, not the implementation.
  - Resolving every host before the run starts: a host whose resolution fails would need a
    second recording path, which spec 003 deliberately keeps in one place.

## R5. Checking the runner and the task kind (FR-001, FR-003, FR-014)

- **Decision:** `_sync_streaming_runner` and `_async_streaming_runner` gain a keyword
  argument that skips the task-kind check, so `run_operation` checks only the runner kind
  before the run. The task kind is checked per host in `_resolve_call`: on the synchronous
  path, an `async def` implementation raises `AsyncTaskOnSyncRunError`; on the asynchronous
  path, a `def` implementation raises `SyncTaskOnAsyncRunError`. Both are `Exception`
  subclasses, so the host fails and the others continue.
- **Rationale:** The kind is only known once the implementation is selected. The existing
  error classes and messages are reused.
- **Alternatives rejected:** raising before the run if any selected host would mismatch:
  that is a preflight check, out of scope.

## R6. Input validation (FR-007, FR-008, FR-009)

- **Decision:** One function, `_build_input(model, value)`:
  1. `None`: call `model()`.
  2. An instance of `model`: use it as it is.
  3. If `model` has a callable `model_validate`: call it with the value (Pydantic and
     compatible libraries).
  4. A mapping: call `model(**value)`.
  5. Anything else: fail.

  Any exception from steps 1, 3 or 4, and step 5, raises `OperationInputError` with the
  original exception as `__cause__`. For a `TypeError` about an unexpected keyword, the
  message adds the closest field name from `inspect.signature(model)` with
  `difflib.get_close_matches` ("did you mean 'sanitized'?").

  A static value is built once in `run_operation`, before the run, and the same instance is
  given to every host, as keyword arguments are today. A callable is called in
  `_resolve_call`, and its return value goes through the same function.
- **Rationale:** Core needs only "build from user data" and "is an instance". `model_validate`
  is detected by duck typing, so core never imports Pydantic (FR-009).
- **Alternatives rejected:** copying the static instance per host: the models are
  user-defined and may not be copyable; plain tasks already share keyword arguments.

## R7. Output validation and `Result` returns (FR-010, FR-011)

- **Decision:** `_finish` already wraps a plain return value in `Result`. `_check_result`
  then applies: if `result.failed`, return it unchanged; otherwise, if
  `isinstance(result.result, output_model)` is false, return a new failed `Result` whose
  exception is `OperationOutputError`, and keep the original value in the message only by
  its type name. `changed`, `diff` and `severity_level` of a valid `Result` are kept as the
  implementation set them.
- **Rationale:** One check for both return forms. `isinstance` works for dataclasses and
  Pydantic models alike.
- **Alternatives rejected:** re-validating the output through `model_validate`: it would
  coerce a wrong value into a valid one, hiding implementation bugs.

## R8. The registry: its own class, not `PluginRegister` (FR-015 to FR-020)

- **Decision:** A new `OperationRegistry` class with class-level state and class methods
  (`register`, `deregister`, `get`, `operations`, `load`), guarded by one
  `threading.Lock`. It stores contracts by name and registrations by
  `(operation, platform, connection)`, each with a `RegistrationSource`.
- **Rationale:** `PluginRegister` maps a name to one plugin and records no source. Its
  `available` dict is a class attribute that every `PluginRegister` instance shares, which
  is not a model to extend. The issue's examples already call
  `OperationRegistry.register(...)` on the class.
- **Alternatives rejected:** subclassing `PluginRegister`: the key is a triple, and sources
  and the `replace` rule do not fit its interface.

## R9. When entry points are loaded (FR-015, FR-016, SC-004)

- **Decision:** `OperationRegistry.load()` reads both entry-point groups once per process,
  on the first call to any method that reads the registry (`get`, `operations`, and through
  them `run_operation`). It is not called from `InitNornir`. `load()` is idempotent and
  thread-safe; a conflict or a malformed name raises from that first call, and the next
  call tries again.
- **Rationale:** Loading imports every installed implementation module. Doing that in
  `InitNornir` would make a broken or conflicting Operations package break programs that
  never use Operations, contrary to SC-004 and to the reason plugins were unbundled
  (Principle II). Loading on first use still raises the conflict before any device is
  contacted.
- **Alternatives rejected:** loading in `InitNornir`, as connection plugins are: see above.

## R10. Entry-point groups and names (FR-015, FR-015a)

- **Decision:**
  - `nornir.plugins.operations`: contracts. Name = Operation name; value = the Operation
    class. Loading the entry point imports the module, which registers the class (R3); the
    loader then checks that the class's `name` equals the entry-point name.
  - `nornir.plugins.operation_tasks`: implementations. Name = `<operation>.<platform>.<connection>`;
    value = the task. A name that does not split into exactly three non-empty parts on `.`
    raises `OperationEntryPointError` naming the distribution and the entry point.

  The source of an entry-point registration is `entry_point.dist.name` (available from
  Python 3.10) and the entry point's `name` and `value`.
- **Rationale:** Fixed groups can be listed (`importlib.metadata.entry_points(group=...)`),
  which FR-019 needs. Both names follow the existing `nornir.plugins.*` pattern
  (`nornir.plugins.connections`, `nornir.plugins.runners`, …), so Principle II needs no
  amendment.
- **Alternatives rejected:** one group per Operation, as in the issue: cannot be listed
  (spec Clarifications).

## R11. Conflicts and re-definitions (FR-016, FR-018)

- **Decision:**
  - Registering the same task object again under the same key is accepted.
  - A different task under a taken key raises `OperationAlreadyRegisteredError` with both
    sources, unless `register(..., replace=True)`. Entry points always register with
    `replace=False`.
  - A second contract class with the same `name` raises `OperationAlreadyRegisteredError`,
    **unless** it has the same `__module__` and `__qualname__` as the registered one, in
    which case it replaces it.
- **Rationale:** The exception for the same module and qualified name covers a notebook
  cell or a module that is executed again: the class object is new, but it is the same
  definition. Without it, re-running a notebook cell that defines an Operation would fail.
- **Alternatives rejected:** comparing class objects only: breaks notebooks and
  `importlib.reload`.

## R12. The default connection (FR-005)

- **Decision:** A new parameter `core.operation_connection` (environment variable
  `NORNIR_CORE_OPERATION_CONNECTION`) in `CoreConfig`. The connection is resolved in
  `run_operation` before the run: `connection or self.config.core.operation_connection`.
  When neither is set, `OperationConnectionNotSetError` is raised and no stream is
  returned.
- **As implemented:** the existing `Parameter` class cannot hold `None`, so the
  parameter is a `str` and the empty string means unset, as for
  `inventory.transform_function`. `CoreConfig.dict()` leaves the key out while it is
  unset, so `Config.dict()` returns the same value as before for programs that do not
  use Operations.
- **Rationale:** `CoreConfig` already holds settings that apply to every run
  (`raise_on_error`). Adding a parameter to an existing section changes no signature of
  `InitNornir`, `Config` or `Config.from_dict`.
- **Alternatives rejected:** a new `operations:` section: it needs a new keyword argument on
  `InitNornir`, `AInitNornir`, `Config`, `from_dict` and `from_file`, for one value.

## R13. Errors (SC-003)

- **Decision:** A base `OperationError(Exception)` with seven subclasses in
  `nornir/core/exceptions.py`: `OperationInputError`, `OperationOutputError`,
  `OperationNotRegisteredError`, `OperationAlreadyRegisteredError`,
  `OperationConnectionNotSetError`, `OperationEntryPointError`,
  `OperationContractNotFoundError`. Fields are strings, and each class defines
  `__reduce__`, as the spec 003 errors do. The task-kind mismatch reuses the existing
  `SyncAsyncMismatchError` subclasses, which gain optional `operation` and `host_name`
  arguments so that the message names both (SC-003); without them the message is
  unchanged. Full list in [contracts/errors.md](contracts/errors.md).
- **Rationale:** One base class lets callers catch every Operation error at once; picklable
  errors match spec 003.

## R14. Listing without calling (FR-019)

- **Decision:** `OperationRegistry.operations()` calls `load()`, then returns one
  `OperationInfo` per known name, sorted by name. Each holds the contract class (or `None`
  for a name with implementations but no contract), its two models, and a tuple of
  `Registration` objects. Each registration reports its kind (`"sync"` or `"async"`),
  computed with the existing `_is_async_task`. No task is called.
- **Rationale:** Loading imports the task modules (R9). The kind of a task can only be read
  from the task itself, so FR-019 permits importing and forbids only calling.
