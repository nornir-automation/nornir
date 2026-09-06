---

description: "Task list for the asyncio runner feature"
---

# Tasks: Asyncio Runner

**Input**: Design documents from `/specs/001-asyncio-runner/`

**Prerequisites**: plan.md, spec.md, research.md (decisions R1–R16), data-model.md, contracts/
(protocols.py, entry-points.md, errors.md), quickstart.md

**Tests**: Included. The specification mandates a test-only reference plugin (FR-018) and the
constitution (Principle IV) requires every behavioural change to arrive with tests. Within each
story the test tasks come first and must fail before the implementation task that makes them pass.

**Organization**: Tasks are grouped by user story. The four stories ship together in one release
(spec), but each phase is independently testable so implementation can stop and validate at every
checkpoint.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story the task belongs to (US1–US4)
- Every task names the exact file(s) it touches

## Path Conventions

Single library project at the repository root: `nornir/` (package), `tests/` (pytest, mirrors the
package layout), `docs/` (Sphinx + executed notebooks). Loops: `make pytest`, `make mypy`,
`make ruff`, `make nbval`, `make docs`; the authoritative gate is `make tests`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package scaffolding for the new test modules; nothing user-visible yet.

- [X] T001 [P] Create `tests/plugins/runners/__init__.py` (empty) so `tests/plugins/runners/` is a test package mirroring `nornir/plugins/runners/`
- [X] T002 [P] Create `tests/plugins/connections/__init__.py` (empty) so `tests/plugins/connections/` is a test package for the `AsyncEcho` fixture and its test
- [X] T003 Run `make pytest` and `make mypy` to record the green baseline before any core change (no file edits; note the pass counts in the PR description later)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared building blocks every story relies on: the named errors, the coroutine-function
detector, the sync/async-neutral refactors of `Task` and `Nornir.run`, and the async runner
contract. Behaviour of the synchronous path must be identical after this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add `SyncAsyncMismatchError(Exception)` and the six subclasses `SyncTaskOnAsyncRunError(task_name)`, `AsyncTaskOnSyncRunError(task_name)`, `RunnerNotSyncError(runner_name)`, `RunnerNotAsyncError(runner_name)`, `ConnectionPluginNotAsyncError(connection_name)`, `ConnectionPluginNotSyncError(connection_name)` plus the module constant `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE = "https://github.com/nornir-automation/nornir/issues/1085"` to `nornir/core/exceptions.py`; each stores its argument as an attribute and its `__str__` contains the pointers listed in `specs/001-asyncio-runner/contracts/errors.md` (research R4)
- [ ] T005 [P] Add the private helper `_is_coroutine_function(obj: object) -> bool` to `nornir/core/task.py` using `inspect.iscoroutinefunction`, falling back to `type(obj).__call__` for callable instances (research R3)
- [ ] T006 [P] Add the optional sibling Protocol `AsyncRunnerPlugin` (`__init__(*args, **kwargs)`, `async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult`) to `nornir/core/plugins/runners.py` exactly as in `specs/001-asyncio-runner/contracts/protocols.py`; leave `RunnerPlugin` and `RunnersPluginRegister` untouched (research R2)
- [ ] T007 Refactor `Task.start` in `nornir/core/task.py` onto three private helpers with no behaviour change: `_begin(host)` (set `self.host`, emit `task_instance_started`/`subtask_instance_started`, debug log), `_result_from_exception(host, exc)` (the two existing `except` branches returning a failed `Result`), `_finish(host, r)` (coerce non-`Result`, set name and severity, `results.insert(0, r)`, emit `*_instance_completed`, return `self.results`); keep `except Exception` (not `BaseException`) (research R5)
- [ ] T008 Refactor `Task.run` in `nornir/core/task.py` onto `_new_subtask(task, kwargs) -> Task` (the host-set check, `severity_level` inheritance, `Task(..., parent_task=self)`) and `_record_subtask(run_task, r) -> MultiResult` (append `r[0]` or `r`, raise `NornirSubTaskError` if failed), with `run` calling `start` between them; no behaviour change (research R5)
- [ ] T009 Refactor `Nornir.run` in `nornir/core/__init__.py` onto `_prepare_run(task, name, kwargs) -> tuple[Task, list[Host]]` (build `Task`, emit `task_started`, select hosts by `on_good`/`on_failed`, the existing info/warning logs) and `_finish_run(run_task, result, raise_on_error) -> AggregatedResult` (resolve `raise_on_error`, `result.raise_on_error()` or update `data.failed_hosts`, emit `task_completed`); `run` = `_prepare_run` → `self.runner.run` → `_finish_run` (research R7)
- [ ] T010 Run `make pytest`, `make mypy`, `make ruff` and confirm the pre-existing suite passes unmodified after T004–T009 (FR-020 check on the refactors; no file edits)

**Checkpoint**: Foundation ready. Synchronous behaviour unchanged; errors and contract exist.

---

## Phase 3: User Story 1 - Run async tasks from inside an event loop (Priority: P1) 🎯 MVP

**Goal**: Select `runner: asyncio`, write an `async def` task, `await nr.arun(task)` from a running
loop, and get the same `AggregatedResult`, processor events and `failed_hosts` bookkeeping as a
threaded run; `await task.arun(subtask)` inside the task; every wrong sync/async task or runner
combination raises its named error before any host starts.

**Independent Test**: With the test inventory and a task that awaits a short sleep, `nr.arun`
completes with one entry per host, at most `num_workers` hosts are in flight, a heartbeat coroutine
is never starved, and the seven task/runner error surfaces raise the named classes. No connection
plugin involved.

### Tests for User Story 1

> Write these first; they must fail (ImportError/AttributeError or wrong behaviour) before T017–T022.

- [ ] T011 [P] [US1] Create `tests/plugins/runners/test_asyncio.py` with `asyncio.run()`-driven tests (research R10) for `AsyncioRunner`: results keyed by host name in host order; at most `num_workers` hosts in flight (count concurrent entries with a shared counter in the task); a raising task records a failed `Result` and does not stop other hosts; `num_workers` larger than the host count runs all hosts concurrently; zero hosts returns an empty `AggregatedResult`; `AsyncioRunner().run(...)` raises `RunnerNotSyncError`; `AsyncioRunner().num_workers == 20`
- [ ] T012 [P] [US1] Add to `tests/plugins/runners/test_asyncio.py` the two performance tests from research R11: `test_thousand_hosts_under_two_seconds` (1,000 in-memory `Host` objects, `asyncio.sleep(0.1)` task, `num_workers=1000`, wall clock < 2 s, `threading.active_count()` unchanged; SC-003) and `test_sibling_coroutine_not_starved` (100 hosts, heartbeat coroutine sleeping 10 ms recording max gap with `time.monotonic()`, assert max gap < 0.05 s; SC-002)
- [ ] T013 [P] [US1] Create `tests/core/test_async_run.py` with a recording processor and tests for `Nornir.arun` on `nornir.with_runner(AsyncioRunner())`: returns `AggregatedResult` with one `MultiResult` per host; processor event sequence and arguments equal to a `SerialRunner` run of the equivalent `def` task (`task_started`, per-host started/completed, `task_completed`); a failing host is added to `nr.data.failed_hosts` and skipped by the next `arun` with default `on_good`/`on_failed`; `raise_on_error=True` raises `NornirExecutionError`; `arun` accepts `name=` and task kwargs like `run`
- [ ] T014 [P] [US1] Add to `tests/core/test_async_run.py` the error-matrix tests, each asserting the recording processor saw no `task_instance_started`: `nr.arun(def_task)` → `SyncTaskOnAsyncRunError` whose message contains `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE`; `nr.arun(async_task)` on the conftest `SerialRunner` → `RunnerNotAsyncError`; `nr.run(async_task)` on `SerialRunner` → `AsyncTaskOnSyncRunError` (not a coroutine stored as success); `nr.run(def_task)` on `AsyncioRunner` → `RunnerNotSyncError`
- [ ] T015 [P] [US1] Create `tests/core/test_async_tasks.py` with tests for `Task.arun`/`astart` on `AsyncioRunner`: `await task.arun(async_subtask)` appends to the parent's results and emits `subtask_instance_started/completed`; a raising async subtask records a failed `Result`, raises `NornirSubTaskError` in the parent and marks the host failed; `task.run(def_subtask)` inside an `async def` task runs inline and records normally (FR-009); `task.run(async_subtask)` inside an async task → `AsyncTaskOnSyncRunError`; `task.arun(def_subtask)` → `SyncTaskOnAsyncRunError`; `task.run(async_subtask)` inside a `def` task on `SerialRunner` → `AsyncTaskOnSyncRunError`
- [ ] T016 [US1] Update the single pre-existing assertion in `tests/core/test_registered_plugins.py::test_registered_runners` to expect `{"threaded": ThreadedRunner, "serial": SerialRunner, "asyncio": AsyncioRunner}` (import `AsyncioRunner` from `nornir.plugins.runners`); this is the SC-001 deviation recorded in plan.md

### Implementation for User Story 1

- [ ] T017 [US1] Add `async def astart(self, host: Host) -> MultiResult` to `Task` in `nornir/core/task.py`: `_begin(host)`; `try: r = await self.task(self, **self.params)`; `except Exception as e: r = self._result_from_exception(host, e)`; `return self._finish(host, r)`; `BaseException` (incl. `asyncio.CancelledError`) propagates unrecorded (contracts/entry-points.md)
- [ ] T018 [US1] Add `async def arun(self, task: Callable[..., Coroutine[Any, Any, Any]], **kwargs: Any) -> MultiResult` to `Task` in `nornir/core/task.py`: raise `SyncTaskOnAsyncRunError(getattr(task, "__name__", repr(task)))` if not `_is_coroutine_function(task)`; `run_task = self._new_subtask(task, kwargs)`; `r = await run_task.astart(self.host)`; `return self._record_subtask(run_task, r)`; and make `Task.run` raise `AsyncTaskOnSyncRunError` first when `_is_coroutine_function(task)` (FR-010)
- [ ] T019 [US1] In `nornir/core/__init__.py` add the private `TypeGuard` helper `_is_async_runner(runner: object) -> TypeGuard[AsyncRunnerPlugin]` (checks `inspect.iscoroutinefunction(getattr(runner, "arun", None))`) and make `Nornir.run` raise `AsyncTaskOnSyncRunError` before `_prepare_run` when `_is_coroutine_function(task)` (FR-006)
- [ ] T020 [US1] Add `async def arun(self, task, raise_on_error=None, on_good=True, on_failed=False, name=None, **kwargs) -> AggregatedResult` to `Nornir` in `nornir/core/__init__.py` with the signature from `specs/001-asyncio-runner/contracts/entry-points.md`: raise `SyncTaskOnAsyncRunError` if the task is not a coroutine function, raise `RunnerNotAsyncError(type(self.runner).__name__)` if not `_is_async_runner(self.runner)`, then `_prepare_run` → `await self.runner.arun(run_task, run_on)` → `_finish_run`; docstring mirrors `run`
- [ ] T021 [US1] Add `class AsyncioRunner` to `nornir/plugins/runners/__init__.py`: `__init__(self, num_workers: int = 20)`; `run()` raises `RunnerNotSyncError("AsyncioRunner")`; `async def arun(task, hosts)` creates `asyncio.Semaphore(self.num_workers)` per call, schedules `asyncio.ensure_future(_run_host(host))` per host where `_run_host` does `async with semaphore: return await task.copy().astart(host)`, `await asyncio.gather(*futures)`, and builds `AggregatedResult(task.name)` keyed by `host.name` in host order; module and class docstrings in the style of `ThreadedRunner` (research R6; cancellation drain is T034)
- [ ] T022 [US1] Register the runner in `pyproject.toml` under `[project.entry-points."nornir.plugins.runners"]` as `asyncio = "nornir.plugins.runners:AsyncioRunner"` and run `uv sync --locked` so the entry point is visible to `RunnersPluginRegister.auto_register()` (research R1)
- [ ] T023 [US1] Run `make pytest ARGS="tests/plugins/runners tests/core/test_async_run.py tests/core/test_async_tasks.py tests/core/test_registered_plugins.py"`, then `make mypy` and `make ruff`; fix until green with no new `# type: ignore` / `# noqa` (Principle III)

**Checkpoint**: US1 is fully functional: async tasks run on the caller's loop with identical
result/processor/failed-host semantics, and every task/runner mismatch raises its named error.

---

## Phase 4: User Story 2 - Plug in an async connection plugin (Priority: P1)

**Goal**: An optional `AsyncConnectionPlugin` contract (`aopen`, `aclose`, `connection`) registered
through the existing entry-point group, with `Host.aget_connection` / `aopen_connection` /
`aclose_connection` / `aclose_connections` sharing the per-host cache keyed by name; sync plugins
untouched; mismatches raise the two connection errors.

**Independent Test**: The standard-library-only `AsyncEcho` fixture talking to a local echo server:
an async task obtains the connection, sends a payload, receives it back, a second call reuses the
cached connection, and `aclose_connections` empties the host's table. Runs on Linux, macOS, Windows.

### Tests for User Story 2

- [ ] T024 [P] [US2] Create `tests/core/test_async_connections.py` with three dummy plugins (sync-only: a copy of `DummyConnectionPlugin` from `tests/core/test_connections.py`; async-only: `aopen`/`aclose`/`connection` only, recording an `aopen_calls` counter; both: the sync dummy plus `aopen`/`aclose` — SC-005) registered in `setup_class`/`teardown_method` like `tests/core/test_connections.py`, and tests driven by `nornir.with_runner(AsyncioRunner())` + `asyncio.run()`: `aget_connection` awaits `aopen` once with the host's resolved parameters and a second call returns the cached connection without reopening (US2-1); `aget_connection` on sync-only → `ConnectionPluginNotAsyncError` (US2-2); `get_connection` from a `def` task on async-only → `ConnectionPluginNotSyncError` (US2-3); a connection opened through `get_connection` is returned by `aget_connection` for the same name with `aopen_calls == 0` (US2-4); two concurrent `aget_connection` calls for one name via `asyncio.gather` make exactly one raise `ConnectionAlreadyOpen` and leave one connection; `aopen` raising leaves the name absent from `connections`; `aclose_connections` awaits `aclose` on async plugins and calls `close` on sync ones (mixed host; FR-014); sync `close_connection` on an async-only connection → `ConnectionPluginNotSyncError`
- [ ] T025 [P] [US2] Create the fixture plugin `tests/plugins/connections/async_echo.py` per research R12: fully typed, standard library only, module docstring explaining it is a protocol reference not a transport; `EchoConnection` (`reader`, `writer`, `async def send(payload: bytes) -> bytes` doing write/drain/`readexactly(len(payload))`); `AsyncEcho` with `async def aopen(hostname, username, password, port, platform, extras=None, configuration=None)` calling `asyncio.open_connection(hostname, port)`, an idempotent `async def aclose()` (close writer, `await wait_closed()`, set `_connection = None`, no-op when already closed), and the `connection` property; no test imports (the docs `literalinclude` this file)
- [ ] T026 [P] [US2] Create `tests/plugins/connections/test_async_echo.py`: inside each test's `asyncio.run()` scope start `asyncio.start_server(echo_handler, "127.0.0.1", 0)`, read the port from `server.sockets[0].getsockname()[1]`, register `AsyncEcho` as `"async_echo"` in `ConnectionPluginRegister` (deregister in teardown), point the test hosts at that port via `ConnectionOptions`, and assert through `nr.arun` with `AsyncioRunner(num_workers=2)`: every host sends and receives its own payload; a second `aget_connection` in the same task reuses the connection; after `await nr.aclose_connections()` every host's `connections` is empty; a second `aclose` on the plugin is a no-op (US2 independent test, FR-018, Principle IV)

### Implementation for User Story 2

- [ ] T027 [US2] Add the optional sibling Protocol `AsyncConnectionPlugin` (`aopen` with the same parameters and order as `open`, `aclose`, `connection` property) to `nornir/core/plugins/connections.py` exactly as in `specs/001-asyncio-runner/contracts/protocols.py`, with a docstring stating the two author rules; leave `ConnectionPlugin` and `ConnectionPluginRegister` unchanged (research R8)
- [ ] T028 [US2] In `nornir/core/inventory.py` add the private `TypeGuard` helpers `_has_async_members(plugin) -> TypeGuard[AsyncConnectionPlugin]` (coroutine-function `aopen`) and `_has_sync_members(plugin) -> TypeGuard[ConnectionPlugin]` (callable `open`), add `"_opening"` to `Host.__slots__` and initialise `self._opening: set[str] = set()` in `Host.__init__` (research R9)
- [ ] T029 [US2] Add `async def aopen_connection(...) -> AsyncConnectionPlugin` to `Host` in `nornir/core/inventory.py` with the same parameters and defaulting logic as `open_connection`: raise `ConnectionAlreadyOpen(conn_name)` if the name is in `connections` or `_opening`; instantiate the registered plugin; raise `ConnectionPluginNotAsyncError(conn_name)` unless `_has_async_members`; add to `_opening`; `try: await conn_obj.aopen(...)` `finally: self._opening.discard(conn_name)`; store in `connections` and return it
- [ ] T030 [US2] Add `async def aget_connection(self, connection: str, configuration: Config) -> Any` to `Host` in `nornir/core/inventory.py`: raise `ConnectionAlreadyOpen(connection)` if the name is in `_opening`; if absent from `connections`, resolve parameters with `get_connection_parameters` and `await self.aopen_connection(...)` exactly as `get_connection` does; return `self.connections[connection].connection`
- [ ] T031 [US2] Add `async def aclose_connection(self, connection: str) -> None` (raise `ConnectionNotOpen` if absent; pop; `await aclose()` if `_has_async_members` else `close()`) and `async def aclose_connections(self) -> None` (snapshot keys, await `aclose_connection` for each) to `Host` in `nornir/core/inventory.py` (FR-014)
- [ ] T032 [US2] Add the sync-side guards in `nornir/core/inventory.py`: `open_connection` raises `ConnectionPluginNotSyncError(conn_name)` after instantiation when not `_has_sync_members(conn_obj)`; `close_connection` raises `ConnectionPluginNotSyncError(conn_name)` when the stored plugin has no callable `close` (pop only after the check so the connection is not lost) (FR-013)
- [ ] T033 [US2] Run `make pytest ARGS="tests/core/test_async_connections.py tests/plugins/connections tests/core/test_connections.py tests/core/test_pickle.py"` (pickle covers the new slot), then `make mypy` and `make ruff`; fix until green

**Checkpoint**: US1 and US2 work independently; the full async connection path is exercised by a
real socket on every platform in CI.

---

## Phase 5: User Story 3 - Clean up connections in an async context (Priority: P2)

**Goal**: `async with nr:` and `await nr.aclose_connections()` close every connection, sync or
async, on good and failed hosts, as a task the processors observe; the synchronous `with nr:` and
`nr.close_connections()` on the `asyncio` runner raise `RunnerNotSyncError`.

**Independent Test**: Open one sync and one async connection on a host inside a run, mark a second
host failed, exit the `async with` block; every host's connection table is empty and a recording
processor saw the cleanup task's `task_started`.

### Tests for User Story 3

- [ ] T034 [P] [US3] Add to `tests/core/test_async_run.py` (reusing the dummies from `tests/core/test_async_connections.py` via import or local copies) tests for: `async with nr:` closes connections of good and failed hosts alike (US3-1); a host holding one sync and one async connection has both closed by `await nr.aclose_connections()` with `aclose` awaited and `close` called (US3-2); the recording processor sees `task_started` for the cleanup task and `on_good`/`on_failed` are honoured (US3-3); on `AsyncioRunner`, `nr.close_connections()` and `with nr:` exit raise `RunnerNotSyncError` (US3-4, FR-007); on `SerialRunner`, `await nr.aclose_connections()` and `async with nr:` exit raise `RunnerNotAsyncError`

### Implementation for User Story 3

- [ ] T035 [US3] Add `async def aclose_connections(self, on_good: bool = True, on_failed: bool = False) -> None` to `Nornir` in `nornir/core/__init__.py`, defining an inner `async def aclose_connections_task(task: Task) -> None: await task.host.aclose_connections()` and running it through `await self.arun(task=aclose_connections_task, on_good=on_good, on_failed=on_failed)`; docstring mirrors `close_connections` (FR-015)
- [ ] T036 [US3] Add `async def __aenter__(self) -> Nornir` (return `self`) and `async def __aexit__(self, exc_type, exc_val, exc_tb) -> None` (await `self.aclose_connections(on_good=True, on_failed=True)`) to `Nornir` in `nornir/core/__init__.py`, typed like the existing `__exit__`
- [ ] T037 [US3] Run `make pytest ARGS="tests/core/test_async_run.py"`, `make mypy`, `make ruff`; fix until green

**Checkpoint**: Async applications can open, run and clean up without leaking device sessions.

---

## Phase 6: User Story 4 - Cancel a run in progress (Priority: P3)

**Goal**: Cancelling the awaiting `arun` cancels every in-flight host, propagates to the caller, and
records nothing: no result, no `failed_hosts` change, no `task_completed`, no host coroutine left
pending.

**Independent Test**: Start a run whose task awaits a long sleep, cancel the awaiting task after
the first host has started, and assert `CancelledError` at the caller, `asyncio.all_tasks()` free of
host coroutines, `failed_hosts` unchanged, and no `task_completed` recorded.

### Tests for User Story 4

- [ ] T038 [P] [US4] Add `test_cancel_propagates` and `test_cancel_records_nothing` to `tests/plugins/runners/test_asyncio.py`: wrap `nr.arun(long_sleep_task)` in `asyncio.ensure_future`, wait on an `asyncio.Event` set by the first host, call `.cancel()`, assert `pytest.raises(asyncio.CancelledError)` on awaiting it, then assert `asyncio.all_tasks()` contains only the current task, `nr.data.failed_hosts` is unchanged, the recording processor got `task_started` but no `task_completed`, and twenty hosts (`num_workers=20`) were all in flight when cancelled (US4-1, US4-2, FR-016)

### Implementation for User Story 4

- [ ] T039 [US4] Add the cancel-and-drain block to `AsyncioRunner.arun` in `nornir/plugins/runners/__init__.py`: wrap the `await asyncio.gather(*futures)` in `try/except BaseException:` that cancels every future, awaits `asyncio.gather(*futures, return_exceptions=True)`, and re-raises; document in the `arun` docstring that cancellation propagates and records nothing (research R6, contracts/protocols.py)
- [ ] T040 [US4] Run `make pytest ARGS="tests/plugins/runners"`, `make mypy`, `make ruff`; fix until green

**Checkpoint**: All four stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation (Principle V), changelog, the merge precondition, and the full gate.

- [ ] T041 [P] Create `docs/howto/asyncio_runner/config.yaml` (`inventory: plugin: SimpleInventory` with `host_file`/`group_file`/`defaults_file` under `asyncio_runner/inventory/`, and `runner: plugin: asyncio` with `options: num_workers: 100`) and `docs/howto/asyncio_runner/inventory/{hosts,groups,defaults}.yaml` with three hosts, modelled on `docs/howto/handling_connections/`
- [ ] T042 Create and execute `docs/howto/asyncio_runner.ipynb` (kernel cwd `docs/howto/`) covering, as real output: `InitNornir(config_file="asyncio_runner/config.yaml")` and `nr.runner`; an `async def` task awaiting `asyncio.sleep`; top-level `await nr.arun(task)` and printing per-host results; `await task.arun(subtask)`; `async with nr:`; and the named errors each printed from a `try/except SyncAsyncMismatchError as exc: print(type(exc).__name__, exc)` cell (`nr.arun(def_task)`, `nr.run(async_task)`, `nr.with_runner(ThreadedRunner()).run(async_task)`); no timings printed; commit the notebook exactly as executed (research R13, FR-019, SC-006)
- [ ] T043 [P] Create `docs/howto/writing_async_connection_plugins.rst`: when to implement `AsyncConnectionPlugin`, the sibling relationship to `ConnectionPlugin`, `.. literalinclude:: ../../tests/plugins/connections/async_echo.py` with `:language: python`, the two rules (`aopen`/`aclose` must not block the loop; `aclose` must be safe to call more than once), a "both contracts in one class" example with unchanged `[project.entry-points."nornir.plugins.connections"]` registration, and usage via `await task.host.aget_connection(name, task.nornir.config)` (FR-019)
- [ ] T044 [P] Update `docs/plugins/index.rst` (Connections: mention `AsyncConnectionPlugin` and link to `../howto/writing_async_connection_plugins`; Runners: note `AsyncioRunner` and link to `../howto/asyncio_runner`), `docs/plugins/execution_model.rst` (a paragraph on the `asyncio` model: coroutines on the caller's loop bounded by `num_workers`, no threads), and `docs/configuration/parameters.rst` (`runner.plugin` description lists `serial`, `threaded`, `asyncio`; default stays `threaded`)
- [ ] T045 [P] Add a `3.7.0 - unreleased` section at the top of `CHANGELOG.rst` with entries for: the `asyncio` runner, `Nornir.arun`/`aclose_connections`/`async with`, `Task.astart`/`arun`, the `AsyncConnectionPlugin` contract and `Host.a*` connection methods (#1085); and the one synchronous-path change: an `async def` task given to `nr.run()`/`task.run()` now raises `AsyncTaskOnSyncRunError` instead of recording the coroutine as a successful result
- [ ] T046 Open the follow-up GitHub issue "Synchronous tasks in async runs" (thread-backed execution and its opt-in surface, per spec Assumptions and #1085 question 2) and replace the URL in `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE` in `nornir/core/exceptions.py` with the new issue's URL; update the assertion in `tests/core/test_async_run.py` if it hard-codes the number (merge precondition)
- [ ] T047 Run `make tests` (ruff, mypy, nbval, pytest, docs) on the local platform and confirm `git status` shows no change under `docs/api/` after `make docs` (plan: no module added or removed)
- [ ] T048 Walk through `specs/001-asyncio-runner/quickstart.md` sections 1–4 and tick its pre-PR checklist; draft the PR description restating maintainer approval for `AsyncioRunner` as an in-tree plugin (Constitution II) and the two spec deviations from `specs/001-asyncio-runner/plan.md`; propose the SC-001 rewording in `specs/001-asyncio-runner/spec.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; T001/T002 in parallel, T003 anytime before Phase 2 edits.
- **Foundational (Phase 2)**: depends on Setup. T004, T005, T006 in parallel; T007 → T008 (same
  file, `task.py`); T009 independent of T007/T008; T010 after all.
- **US1 (Phase 3)**: depends on Phase 2. Tests T011–T015 in parallel, T016 with them;
  T017 → T018 (`task.py`); T019 → T020 (`nornir/core/__init__.py`); T021 → T022; T023 last.
- **US2 (Phase 4)**: depends on Phase 2 and on T020/T021 (tests drive through `nr.arun` on
  `AsyncioRunner`). Tests T024–T026 in parallel; T027 first; T028 → T029 → T030 → T031 → T032
  (all `inventory.py`); T033 last.
- **US3 (Phase 5)**: depends on US1 (uses `arun`) and US2 (uses `Host.aclose_connections`).
  T034 → T035 → T036 → T037.
- **US4 (Phase 6)**: depends on US1 (edits `AsyncioRunner.arun`). T038 → T039 → T040.
- **Polish (Phase 7)**: depends on all stories. T041 → T042 (notebook needs its config);
  T043, T044, T045 in parallel with each other and with T041/T042; T046 anytime after T014;
  T047 after everything else; T048 last.

### User Story Dependencies

- **US1 (P1)**: only the Foundational phase. Delivers the MVP on its own.
- **US2 (P1)**: Foundational plus the `arun` entry point and runner from US1 for its tests; the
  `Host`/protocol implementation itself (T027–T032) does not depend on US1 code.
- **US3 (P2)**: US1 + US2 (composes `arun` with `Host.aclose_connections`).
- **US4 (P3)**: US1 (adds the drain block to the runner written in T021).

### Within Each User Story

- Test tasks first; confirm they fail before the implementation tasks.
- Tasks touching the same file are sequential (`nornir/core/task.py`, `nornir/core/__init__.py`,
  `nornir/core/inventory.py`, `nornir/plugins/runners/__init__.py`).
- Each story ends with its own `make pytest ARGS=...` + `make mypy` + `make ruff` task.

### Parallel Opportunities

- Phase 2: T004 ‖ T005 ‖ T006; T009 ‖ (T007 → T008).
- Phase 3: T011 ‖ T012 ‖ T013 ‖ T014 ‖ T015 ‖ T016; then (T017 → T018) ‖ (T019 → T020) ‖ (T021 → T022).
- Phase 4: T024 ‖ T025 ‖ T026; T027 ‖ T028 (different files), then T029 → T032 sequentially.
- Phase 7: T041 ‖ T043 ‖ T044 ‖ T045; T046 in parallel with the docs tasks.

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (different files):
Task: "T011 AsyncioRunner behaviour tests in tests/plugins/runners/test_asyncio.py"
Task: "T013 Nornir.arun semantics tests in tests/core/test_async_run.py"
Task: "T015 Task.arun/astart tests in tests/core/test_async_tasks.py"
Task: "T016 registry assertion in tests/core/test_registered_plugins.py"

# Then implement across the three source files in parallel streams:
Stream A: "T017 Task.astart" -> "T018 Task.arun + Task.run guard"        (nornir/core/task.py)
Stream B: "T019 _is_async_runner + Nornir.run guard" -> "T020 Nornir.arun" (nornir/core/__init__.py)
Stream C: "T021 AsyncioRunner" -> "T022 entry point in pyproject.toml"   (nornir/plugins/runners/__init__.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup, Phase 2 Foundational (the refactors must leave `make pytest` green: T010).
2. Phase 3 US1: async tasks run on the caller's loop with identical semantics; all task/runner
   mismatches raise named errors.
3. **STOP and VALIDATE**: `make pytest ARGS="tests/plugins/runners tests/core/test_async_run.py tests/core/test_async_tasks.py"`, then the SC-002/SC-003 tests.

### Incremental Delivery

1. US1 → MVP: embeddable in an async application, no connections yet.
2. US2 → async connection plugins plug in; `AsyncEcho` proves the path in CI on all platforms.
3. US3 → cleanup with `async with`; no leaked sessions.
4. US4 → cancellation propagates and records nothing.
5. Phase 7 → executed notebook, plugin-author page, changelog, follow-up issue, `make tests`.

The spec ships all four together in 3.7; the checkpoints are validation points, not release
boundaries.

### Parallel Team Strategy

After Phase 2: one developer on US1 (runner + `Nornir.arun` + `Task.a*`), one on the
`Host`/protocol half of US2 (T027–T032) with its unit tests (T024) stubbed against a temporary
`asyncio.run` harness until `arun` lands; US3 and US4 follow once US1 merges. Docs (T041–T045)
can be drafted in parallel and executed once the code is green.

---

## Notes

- No new runtime or development dependency: tests use `asyncio.run()` (research R10).
- Never add to the ruff or mypy ignore lists without a comment saying why (Principle III).
- Notebook output is committed exactly as executed; never edited by hand (Principle V).
- `docs/api/nornir/**` must not change: no module is added or removed.
- Commit after each task or logical group with Conventional Commits (`feat:`, `test:`, `docs:`).
