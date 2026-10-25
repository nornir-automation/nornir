---
description: "Task list for feature 004: Operations, typed actions across vendors"
---

# Tasks: Operations, Typed Actions Across Vendors

**Input**: Design documents from `specs/004-typed-operations/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required. The constitution (Principle III) and the spec's "Independent Test"
sections ask for tests with every change. Within each story, tests are written first and
must fail before the implementation task runs.

**Organization**: Tasks are grouped by user story, so that each story can be implemented
and tested on its own after Phase 2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task belongs to (US1 to US4)

## Phase 1: Setup

**Purpose**: Confirm the starting point.

- [X] T001 Run `uv sync --locked` and `make pytest` on the branch, and record that the existing suite passes before any change (baseline for FR-023 and SC-004)

---

## Phase 2: Foundational (blocks every user story)

**Purpose**: Generic result types, errors, configuration, the Task hooks and the registry
core that every story uses.

- [X] T002 [P] Make `Result` generic in `nornir/core/task.py`: declare `T` with a type-checker-only default of `Any` (the `TYPE_CHECKING` branch imports `TypeVar` from `typing_extensions`; the runtime branch uses `typing.TypeVar`), as in research R1; annotate `result: T`; keep the constructor signature unchanged
- [X] T003 [P] Make `RunStream`, `RunHandle`, `AsyncRunStream` and `AsyncRunHandle` generic over the same `T` in `nornir/core/run.py`; `results()` yields `Result[T]` and `events()` yields `PartialResult | Result[T]`; existing callers that return them stay valid (bare names mean `[Any]`)
- [X] T004 [P] Add `OperationError` and its seven subclasses (`OperationInputError`, `OperationOutputError`, `OperationNotRegisteredError`, `OperationAlreadyRegisteredError`, `OperationConnectionNotSetError`, `OperationEntryPointError`, `OperationContractNotFoundError`) to `nornir/core/exceptions.py`, with the fields, messages and `__reduce__` defined in [contracts/errors.md](contracts/errors.md)
- [X] T005 [P] Add `operation_connection: Parameter[str | None]` (default `None`, envvar `NORNIR_CORE_OPERATION_CONNECTION`) to `CoreConfig` in `nornir/core/configuration.py`, following the existing `raise_on_error` parameter (research R12)
- [X] T006 Add the private hooks `Task._resolve_call(host) -> tuple[Callable[..., Any], dict[str, Any]]` and `Task._check_result(result) -> Result` to `nornir/core/task.py`; call `_resolve_call` inside the existing `try` of `_start_steps` and `_acall` immediately before the existing `self.task(self, **self.params)` call line (that line itself stays the call site), and `_check_result` in `_finish` for the top-level task only; the base implementations return their inputs unchanged (research R4, R7)
- [X] T007 Create `nornir/core/operations.py` with `Operation(Generic[InT, OutT])` and `__init_subclass__` (reads the models with `get_args(__orig_bases__)`, raises `TypeError` when a type argument is not a class, registers the class when it defines `name`), and the dataclasses `RegistrationSource` (with `__str__` as in data-model.md), `Registration` and `OperationInfo` (research R3, data-model.md)
- [X] T008 Add `OperationRegistry` to `nornir/core/operations.py`: class-level contracts and registrations dicts and one `threading.Lock`; `register` (rejects empty or `None` platform and connection with `ValueError`, accepts the same task twice, raises `OperationAlreadyRegisteredError` naming both sources unless `replace=True`, records a `call` source), `deregister`, `get` (raises `OperationNotRegisteredError` listing the registered keys for that Operation), contract registration with the same-`__module__`-and-`__qualname__` replacement rule (research R8, R11); add a `_reset()` class method for tests only
- [X] T009 Add `_build_input(operation_name, model, value, host_name)` to `nornir/core/operations.py` with the five steps of research R6, the "did you mean" suggestion from `inspect.signature` and `difflib.get_close_matches`, and `OperationInputError` chained to the original exception
- [X] T010 Add a `tests/core/conftest.py` fixture (or extend the existing one) that calls `OperationRegistry._reset()` before and after each test that uses Operations, and a small test inventory with hosts of platform `ios`, `eos`, `junos`, `panos` and `None`

**Checkpoint**: `make mypy` and `make pytest` pass with no behaviour change.

---

## Phase 3: User Story 1 - Run one Operation across vendors (Priority: P1) — MVP

**Goal**: `run_operation` and `submit_operation` (and their asyncio forms) select a task per
host from `(name, platform, connection)` and return typed results.

**Independent Test**: Register `get_config` for `ios.napalm` and `eos.napalm`, run it on
`SerialRunner` and `ThreadedRunner`, check that each host ran its own task and returned a
typed output; type-check the calling code with the repository's mypy settings.

### Tests for User Story 1

- [X] T011 [P] [US1] Write tests in `tests/core/test_operations.py` for quickstart scenarios 1, 2, 3, 6, 7 and 8: dispatch per platform on `SerialRunner` and `ThreadedRunner`; connection from `core.operation_connection` and `OperationConnectionNotSetError`; `submit_operation` handle on `ThreadedRunner` and `RunnerCapabilityError` on `SerialRunner`; `panos` and `platform=None` hosts failing with their own messages while the others succeed; a `dict` output failing with `OperationOutputError`; `params={"sanitize": True}` raising `OperationInputError` with "did you mean 'sanitized'?" before any task runs; `run_operation("get_cfg", ...)` raising `OperationContractNotFoundError`
- [X] T012 [P] [US1] Write tests in `tests/core/test_async_operations.py` for quickstart scenarios 4 and 11: `arun_operation` and `asubmit_operation` with `async def` implementations on `AsyncioRunner`; a run that mixes `def` and `async def` implementations fails only the mismatched host, with `AsyncTaskOnSyncRunError` on `ThreadedRunner` and `SyncTaskOnAsyncRunError` on `AsyncioRunner`
- [X] T013 [P] [US1] Write tests in `tests/core/test_operations.py` for quickstart scenarios 14 and 15: a traceback from a raising implementation has the same number of frames from `nornir/` as the same function run with `nr.run`; `PartialResult`, `task.checkpoint()`, `per_host_timeout` and `cancel()` inside an implementation behave as for a plain task; processors see the implementation task's name
- [X] T014 [P] [US1] Create `tests/core/operations_typing_fixture.py` (checked by `make mypy`): `assert_type(res.result.config, str)` for a class-typed stream, `RunStream[Any]` for a string, and functions annotated with bare `Result`, `RunStream` and `RunHandle`; create `tests/core/test_operations_typing.py` that runs mypy on a snippet with a `lambda` returning the wrong type and asserts the expected error

### Implementation for User Story 1

- [X] T015 [US1] Add `_OperationTask(Task)` to `nornir/core/operations.py` with the fields of data-model.md; override `copy()` to return an `_OperationTask`; override `_resolve_call` (platform `None` check, registry lookup, task-kind check against `path`, per-host callable input through `_build_input`, set `self.task` and `self.params` to the implementation and `{"params": input}`) and `_check_result` (skip when failed, otherwise `isinstance` against `output_model`, else a failed `Result` with `OperationOutputError`)
- [X] T016 [US1] Add a keyword argument to `_sync_streaming_runner` and `_async_streaming_runner` in `nornir/core/__init__.py` that skips the task-kind check (research R5), leaving their behaviour for existing callers unchanged
- [X] T017 [US1] Add `run_operation`, `submit_operation`, `arun_operation` (sync `def`) and `asubmit_operation` (`async def`) to `Nornir` in `nornir/core/__init__.py`, each with the two overloads of [contracts/api.py](contracts/api.py): resolve the contract (class or name, `OperationContractNotFoundError`), the connection (argument, then `config.core.operation_connection`, else `OperationConnectionNotSetError`), build the static input once with `_build_input`, check the runner capability (names `run_operation`, `submit_operation`, `arun_operation`, `asubmit_operation`), build an `_OperationTask` and start the run through the existing `_new_run` path used by `run_stream`, `submit`, `astream` and `asubmit`
- [X] T018 [US1] Make `OperationRegistry.get` call `load()` first; implement `load()` as an idempotent, thread-safe no-op body placeholder that Phase 6 completes (a flag set under the lock), so US1 does not depend on entry points
- [X] T019 [US1] Run `make pytest` and `make mypy`; all tests from T011–T014 pass

**Checkpoint**: User Story 1 works on its own: MVP.

---

## Phase 4: User Story 2 - Report a change from an implementation (Priority: P2)

**Goal**: an implementation can return `Result(result=Out, changed=True, diff=...)`, and a
failed `Result` skips output validation.

**Independent Test**: quickstart scenario 9.

- [X] T020 [P] [US2] Write tests in `tests/core/test_operations.py` for quickstart scenario 9: a `Result` with `changed=True`, a diff and a `severity_level` keeps those fields and passes validation; a `Result(failed=True, exception=err)` fails the host with `err` and is not checked against the output model; a `Result` whose `result` has the wrong type fails with `OperationOutputError`
- [X] T021 [US2] Adjust `_OperationTask._check_result` in `nornir/core/operations.py` if T020 shows a gap (for example, keep `changed`, `diff` and `severity_level` on the original `Result` object rather than a copy); run `make pytest`

**Checkpoint**: User Stories 1 and 2 pass.

---

## Phase 5: User Story 3 - Different parameters for each host (Priority: P3)

**Goal**: `params` can be a callable that receives the host.

**Independent Test**: quickstart scenario 10.

- [X] T022 [P] [US3] Write tests in `tests/core/test_operations.py` for quickstart scenario 10: `params=lambda host: In(path=host.name)` gives each host its own input; a callable that raises for `r2`, and one that returns an invalid value for `r2`, fail only `r2` with `OperationInputError` whose message names the host and whose `__cause__` is the original exception; a mapping returned by the callable is validated
- [X] T023 [US3] Adjust the callable branch of `_OperationTask._resolve_call` and `_build_input` in `nornir/core/operations.py` if T022 shows a gap (for example, wrap an exception raised by the callable itself in `OperationInputError` with `host_name`); run `make pytest`

**Checkpoint**: User Stories 1 to 3 pass.

---

## Phase 6: User Story 4 - List Operations and their implementations (Priority: P4)

**Goal**: entry-point loading, sources, conflicts and listing without calling a task.

**Independent Test**: quickstart scenarios 12 and 13.

### Tests for User Story 4

- [X] T024 [P] [US4] Write tests in `tests/core/test_operations_registry.py` for quickstart scenario 12: same task twice accepted; a different task raises an error naming both sources; `replace=True` replaces and the run uses the new task; `platform=None` and `""` raise `ValueError`; two different Operation classes with one name raise; the same class definition executed twice (via `exec` of the same source with the same module name and qualified name) replaces; an implementation for a name with no contract is accepted and `run_operation("name")` raises `OperationContractNotFoundError`
- [X] T025 [P] [US4] Write tests in `tests/core/test_operations_registry.py` for quickstart scenario 13: build a temporary distribution under `tmp_path` with `pathlib` (a package module, and a `<name>.dist-info/` with `METADATA` and `entry_points.txt`), add it to `sys.path` with `monkeypatch.syspath_prepend`, and check: a contract with no implementation listed with its models and an empty tuple; two implementations listed with `kind` and an `entry_point` source naming the distribution; a malformed name `get_config.ios` raising `OperationEntryPointError` naming the distribution; two distributions declaring different tasks for one key raising `OperationAlreadyRegisteredError` naming both; a failed `load()` retried on the next call; `InitNornir` does not trigger loading

### Implementation for User Story 4

- [X] T026 [US4] Implement `OperationRegistry.load()` in `nornir/core/operations.py`: read `importlib.metadata.entry_points(group="nornir.plugins.operations")` and `group="nornir.plugins.operation_tasks"`; for contracts, load the class and check `name` matches the entry-point name; for implementations, split the name into exactly three non-empty parts or raise `OperationEntryPointError`, then register with `replace=False` and an `entry_point` source (`dist.name`, `"<group>:<name> = <value>"`); mark as loaded only when everything succeeded (research R9, R10, [contracts/entry-points.md](contracts/entry-points.md))
- [X] T027 [US4] Implement `OperationRegistry.operations()` in `nornir/core/operations.py`: call `load()`, return one `OperationInfo` per known name sorted by name, implementations sorted by `(platform, connection)`, each `Registration.kind` computed with `_is_async_task`; no task is called (research R14)
- [X] T028 [US4] Run `make pytest` and `make mypy`; tests from T024 and T025 pass

**Checkpoint**: all four user stories pass.

---

## Phase 7: Polish and cross-cutting concerns

- [X] T029 [P] Create `docs/howto/operations.ipynb`: define `GetConfig` with dataclass models, register implementations for `ios`, `eos` and `junos` with fake tasks that need no device, run it across a three-platform inventory with no platform condition in the calling code, read typed results, show one failure (a `panos` host) and one change report; execute it and commit the real output (SC-001, SC-002); add normalisation to `docs/nbval_sanitize.cfg` only for output that varies between runs
- [X] T030 [P] Link the notebook in `docs/howto/index.rst` (nothing to change: its toctree uses `:glob:` and already includes every notebook in the folder)
- [X] T031 [P] Document `operation_connection` in `docs/configuration/parameters.rst`, following the existing entries
- [X] T032 [P] Add a `CHANGELOG.rst` entry for Operations referencing #1089
- [X] T033 Run `make docs` and keep the regenerated `docs/api/nornir/core/operations.rst` (and any other files it rewrites)
- [X] T034 Check SC-003: confirm that one test covers each of the seven failure cases and that each message names the Operation, the host where one applies, and what to fix; add any missing test to `tests/core/test_operations.py`
- [X] T035 Check SC-004: `git diff main -- pyproject.toml` shows no new runtime dependency, and the existing tests were not modified to pass
- [X] T036 Run `make tests` (ruff, mypy, nbval, pytest, docs); all five gates pass
- [X] T037 Mark the quickstart scenarios as validated; record that scenario 17 (SC-005, a package outside this repository) remains a manual step before release (scenarios 1–16 are covered by the tests; scenario 17 is not done)

---

## Dependencies and execution order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup; blocks every story. T002–T005 can run in
  parallel; T006 depends on T002; T007 to T009 are in one file and run in order after T004;
  T010 after T008.
- **US1 (Phase 3)**: after Phase 2.
- **US2, US3 (Phases 4, 5)**: after US1, because they use `run_operation`; independent of
  each other.
- **US4 (Phase 6)**: after Phase 2 for the registry tests; the run in T024 needs US1.
- **Polish (Phase 7)**: after all stories.

### Within each story

Tests first and failing, then implementation, then `make pytest`. Tasks in
`nornir/core/operations.py` and `nornir/core/__init__.py` run in order, because they edit
the same files.

### Parallel opportunities

- Phase 2: T002, T003, T004, T005.
- Phase 3: T011, T012, T013, T014 (different test files, or independent sections of one
  file written before the implementation).
- After US1: Phases 4, 5 and 6 tests (T020, T022, T024, T025).
- Phase 7: T029, T030, T031, T032.

## Implementation strategy

1. Phases 1 and 2, then check that nothing changed for existing users.
2. Phase 3 (US1): the MVP. Stop and validate: dispatch, typing, errors.
3. Phases 4 and 5: small additions on top of US1.
4. Phase 6: entry points and listing.
5. Phase 7: notebook, docs, changelog, full gate.
