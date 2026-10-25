# Implementation Plan: Operations, Typed Actions Across Vendors

**Branch**: `dga/feat-operation-s0e5v` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Feature directory**: `specs/004-typed-operations`

## Summary

Add Operations, as specified from
[#1089](https://github.com/nornir-automation/nornir/issues/1089): a contract defined once
with a typed input and a typed output, implemented by plain tasks per
`(platform, connection)`, and run across an inventory so that each host returns a typed
result.

- A new module `nornir/core/operations.py` holds `Operation[InT, OutT]`, the
  `OperationRegistry` and a private `_OperationTask(Task)`.
- `Nornir` gains `run_operation` (attached, any streaming runner including
  `SerialRunner`), `submit_operation` (background), and their asyncio counterparts
  `arun_operation` and `asubmit_operation`.
- Dispatch happens per host inside the existing `Task` execution path, through two private
  hooks on `Task`. The implementation is called from the same line as any task, so runners,
  processors, deadlines, cancellation, partial results and `pdb` behave as today.
- `Result` and the four spec 003 run objects become generic, with a default type parameter
  that only the type checker reads. A bare `Result` stays valid under strict mypy, and no
  runtime dependency is added.

## Technical Context

- **Language/version:** Python 3.10–3.14. Standard library only: `typing` (`Generic`,
  `get_args`, `overload`, `TYPE_CHECKING`), `importlib.metadata.entry_points` and
  `EntryPoint.dist` (3.10+), `inspect.signature`, `difflib.get_close_matches`, `threading`,
  `dataclasses`. `typing_extensions` is imported only under `TYPE_CHECKING` (research R1).
- **Dependencies:** no new runtime or development dependency.
- **Storage:** none. Registry state in memory per process (see [data-model.md](data-model.md)).
- **Project type:** pure Python library with structurally typed plugin contracts.
- **Platforms:** Linux, macOS, Windows. No path or shell handling; entry-point test
  fixtures use `pathlib` and a temporary `sys.path` entry.
- **Testing:** `make pytest` during implementation, then `make tests`. One typing fixture
  checked by `make mypy`; expected type errors checked by a pytest that runs mypy on a
  snippet.
- **Performance:** no target. Dispatch adds one dictionary lookup per host. Entry points are
  loaded once per process, on first use.
- **Constraints:** existing signatures, protocol members, defaults, entry points and result
  types unchanged (FR-023). Plain tasks, `run`, `run_stream`, `submit` and processors
  behave exactly as before.
- **Scope:** `nornir/core/operations.py` (new), `nornir/core/task.py`,
  `nornir/core/run.py`, `nornir/core/__init__.py`, `nornir/core/exceptions.py`,
  `nornir/core/configuration.py`; tests; one executed notebook; configuration docs;
  changelog; regenerated API reference.

All unknowns were resolved in [research.md](research.md); none remain open. Two were
checked with probes: the type-checker-only default of R1 (mypy `--strict` and runtime on
3.10, 3.12 and 3.14) and the overloads of R2 (mypy infers the output type from the class,
including through a `lambda`).

## Constitution Check

Design checks assess feasibility, not completed implementation or CI results.

| Principle | Pre-research | Post-design |
|---|---|---|
| I. Python-first, no DSL | PASS: Operations are classes and plain tasks, called from Python | PASS: the implementation is called from the existing `self.task(self, **self.params)` line of `Task`, so tracebacks and `pdb` show the same frames as a plain task (R4, FR-022, quickstart scenario 14) |
| II. Thin core | OPEN: entry points named outside `nornir.plugins.*` in the issue; risk that loading packages breaks unrelated programs | PASS: the core gets a mechanism and a registry, no catalog; groups are `nornir.plugins.operations` and `nornir.plugins.operation_tasks` (R10); entry points load on first use, not in `InitNornir` (R9); no new dependency |
| III. Typed and verified | OPEN: a generic `Result` could break strict downstream projects | PASS at design level: the R1 probe passes `mypy --strict` with bare names, and [contracts/api.py](contracts/api.py) passes mypy with the repository settings |
| IV. Full support matrix | PASS: no platform-specific code | PASS at design level: entry-point fixtures avoid POSIX assumptions; runtime evidence on the matrix remains an implementation gate |
| V. Executable docs | PASS: notebook, docs, changelog in scope | PASS at design level: [quickstart.md](quickstart.md) lists the notebook, the configuration entry, the changelog and the regenerated `operations.rst` |
| VI. Stable public API | OPEN: `Result` changes; new `Nornir` methods | PASS at design level: every change is a new name, a new optional configuration parameter, or a type parameter with a default; no protocol contract changes; MINOR release, no upgrade guide |

**Pre-research disposition:** three checks were open; research R1, R9 and R10 and the two
mypy probes resolve them. No violation is accepted or waived.

**Post-design result:** PASS for task generation. `make tests` and the full matrix remain
required before implementation is complete.

## Design Decisions

### Contracts and registry

1. `Operation.__init_subclass__` reads the models from the type arguments and registers the
   class under `name`; re-executing the same definition replaces it (R3, R11).
2. `OperationRegistry` is a new class with class-level state and one lock, not a
   `PluginRegister` (R8). It records a `RegistrationSource` for every registration (FR-017).
3. Conflicts raise unless `replace=True`; entry points never replace (R11).
4. Entry points load on the first registry read, once per process (R9).

### Running

1. `run_operation` resolves the contract (class or name), the connection (argument, then
   `core.operation_connection`), and a static input, all before the run (R6, R12). Then it
   builds an `_OperationTask` and starts a `RunStream` through the existing `_new_run`.
2. `_sync_streaming_runner` / `_async_streaming_runner` skip the task-kind check for
   Operations; the kind is checked per host (R5).
3. `Task._resolve_call` and `Task._check_result` are the only changes to the execution path
   (R4, R7). Every Operation error for one host is raised inside the existing `try`, so it
   becomes that host's failed `Result`.

### Typing

1. One type variable with a type-checker-only default for `Result` and the four run objects
   (R1). `MultiResult` and `AggregatedResult` stay untyped.
2. Each of the four new methods has two overloads: Operation class (typed) and name string
   (`Any`) (R2).

### Review flags

- **FR-019 wording:** the spec was corrected during planning. Listing may import task
  modules, because the synchronous or asynchronous kind is read from the task (R14).
- **`params` shared across hosts:** a static input instance is given to every host, as
  keyword arguments are today (R6). The notebook should not show an implementation that
  mutates `params`.

## Project Structure

### Feature artifacts

```text
specs/004-typed-operations/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── api.py
│   ├── entry-points.md
│   └── errors.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks
```

### Implementation targets

```text
nornir/core/operations.py             # new: Operation, OperationRegistry, Registration, _OperationTask
nornir/core/task.py                   # Result generic; Task._resolve_call, Task._check_result
nornir/core/run.py                    # RunStream, RunHandle, AsyncRunStream, AsyncRunHandle generic
nornir/core/__init__.py               # run_operation, submit_operation, arun_operation, asubmit_operation
nornir/core/exceptions.py             # OperationError family
nornir/core/configuration.py          # core.operation_connection

tests/core/test_operations.py               # US1, US2, US3 on serial and threaded runners
tests/core/test_async_operations.py         # FR-003, FR-014 on the asyncio runner
tests/core/test_operations_registry.py      # US4, conflicts, sources, entry-point fixture
tests/core/test_operations_typing.py        # runs mypy on expected-error snippets
tests/core/operations_typing_fixture.py     # checked by make mypy (assert_type, bare names)

docs/howto/operations.ipynb           # executed notebook
docs/howto/index.rst                  # link the notebook
docs/configuration/parameters.rst     # operation_connection
docs/api/nornir/core/operations.rst   # regenerated by make docs
CHANGELOG.rst                         # entry referencing #1089
```

**Structure decision:** single library layout; one new core module. `Operation` and the
registry are used by `Nornir` and by implementation packages, and `_OperationTask` needs
`Task`; keeping them out of `nornir/core/__init__.py` avoids an import cycle between
`Nornir` and `Task`.

## Complexity Tracking

No constitution violation to justify.
