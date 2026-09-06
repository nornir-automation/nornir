# Research: Asyncio Runner

**Feature**: 001-asyncio-runner | **Date**: 2026-09-06 | **Plan**: [plan.md](plan.md)

Each entry records a decision the specification left to planning, the rationale, and the
alternatives that were considered. Code facts cited here were read from the repository at the
time of writing (`nornir/core/__init__.py`, `nornir/core/task.py`, `nornir/core/inventory.py`,
`nornir/core/plugins/*.py`, `nornir/plugins/runners/__init__.py`, `pyproject.toml`, `tests/`,
`docs/`).

## R1. Runner name, class and registration

- **Decision**: class `AsyncioRunner` in `nornir/plugins/runners/__init__.py`, registered as
  `asyncio` under `[project.entry-points."nornir.plugins.runners"]` in `pyproject.toml`.
  Constructor `__init__(self, num_workers: int = 20)`. Selectable through `runner.plugin: asyncio`
  with `num_workers` under `runner.options`, and through `nr.with_runner(AsyncioRunner(...))`.
  `InitNornir.load_runner` already instantiates whatever the registry returns with
  `**config.runner.options`, so nothing changes there.
- **Rationale**: fixed by the grilling decision recorded in the spec; the existing runners are
  named after their mechanism (`serial`, `threaded`) and `asyncio` follows suit.
- **Alternatives**: `async` / `AsyncRunner` (the proposal's original name) rejected in the
  grilling session for naming consistency.
- **Consequence**: `tests/core/test_registered_plugins.py::test_registered_runners` asserts the
  registry is exactly `{"threaded", "serial"}`; it must gain `"asyncio": AsyncioRunner`. This is
  the single pre-existing test touched and is recorded as a deviation from SC-001 in the plan.

## R2. Async runner contract and how `Nornir` tells the two kinds apart

- **Decision**: add an optional sibling `AsyncRunnerPlugin` Protocol to
  `nornir/core/plugins/runners.py` with `__init__(*args, **kwargs)` and
  `async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult`. `RunnerPlugin` is
  unchanged. `AsyncioRunner` implements **both**: `run()` raises `RunnerNotSyncError`
  immediately, `arun()` does the work. `Nornir.arun()` decides structurally with a private
  `TypeGuard` helper `_is_async_runner(runner) -> TypeGuard[AsyncRunnerPlugin]` that checks
  `inspect.iscoroutinefunction(getattr(runner, "arun", None))`, and raises
  `RunnerNotAsyncError` when it is false, before any processor event.
- **Rationale**: `Nornir.__init__`, `with_runner` and the `runner` property are typed
  `RunnerPlugin`, and `RunnersPluginRegister` is `PluginRegister[type[RunnerPlugin]]`. Keeping
  a `run()` on `AsyncioRunner` lets it satisfy `RunnerPlugin` structurally, so none of those
  public annotations change (FR-020). A `TypeGuard` gives mypy the narrowing without a `cast`.
- **Alternatives**:
  - Omit `run()` from `AsyncioRunner` so `Nornir.run()` can detect "no sync path" before
    `task_started`. Rejected: it would force `Nornir.runner` to return
    `RunnerPlugin | AsyncRunnerPlugin`, a widened return type that breaks typed downstream code
    calling `nr.runner.run(...)`.
  - `@runtime_checkable` + `isinstance`. Rejected for consistency with R8, where
    `isinstance` against a Protocol with a `connection` property gives wrong answers for plugins
    that only set `connection` inside `open()` (the existing `DummyConnectionPlugin` in
    `tests/core/test_connections.py` does exactly that).
- **Consequence**: `nr.run()` / `nr.close_connections()` / `with nr:` on the `asyncio` runner
  raise `RunnerNotSyncError` from inside `Nornir.run()` after `task_started` has fired. No
  per-host event is emitted (SC-004 holds). Documented in the plan as an accepted asymmetry.

## R3. Detecting an `async def` task

- **Decision**: private helper `_is_coroutine_function(obj: object) -> bool` in
  `nornir/core/task.py`: `inspect.iscoroutinefunction(obj)`, and for a non-function callable
  (an instance with `__call__`) `inspect.iscoroutinefunction(type(obj).__call__)`. Used by
  `Nornir.run` / `Nornir.arun` / `Task.run` / `Task.arun` **before** any processor event. The
  check is not repeated in `Task.start` / `Task.astart`.
- **Rationale**: the spec says "defined with `async def`"; `inspect.iscoroutinefunction` is the
  standard-library test for that and handles `functools.partial` on 3.10+. Callable instances
  are the one gap; checking `__call__` closes it without heuristics. Checking at the four entry
  points keeps `start`/`astart` free of validation and puts the error where the user called.
- **Alternatives**: `asyncio.iscoroutinefunction` (deprecated in 3.14); detecting by calling
  the task and inspecting the return value (rejected: the task has already run at that point).

## R4. Named errors: names, hierarchy, messages

- **Decision**: in `nornir/core/exceptions.py`, a common base
  `SyncAsyncMismatchError(Exception)` and six subclasses:

  | Class | Raised by | Message must point to |
  |---|---|---|
  | `SyncTaskOnAsyncRunError` | `Nornir.arun`, `Task.arun` given a `def` task | define with `async def` or use a synchronous runner; the follow-up issue URL |
  | `AsyncTaskOnSyncRunError` | `Nornir.run` (any sync runner), `Task.run` given an `async def` task | `await nr.arun(...)` / `await task.arun(...)` on the `asyncio` runner, or define with `def` |
  | `RunnerNotSyncError` | `AsyncioRunner.run()` (reached via `Nornir.run`, `close_connections`, `__exit__`) | `await nr.arun(...)` / `await nr.aclose_connections()` / `async with nr:` |
  | `RunnerNotAsyncError` | `Nornir.arun` / `aclose_connections` / `__aexit__` when the runner has no `arun` | `nr.run(...)` / `nr.close_connections()` / `with nr:`, or select the `asyncio` runner |
  | `ConnectionPluginNotAsyncError` | `Host.aget_connection` / `aopen_connection` when the plugin has no `aopen` | `get_connection()` from a synchronous task |
  | `ConnectionPluginNotSyncError` | `Host.get_connection` / `open_connection` / `close_connection` when the plugin has no `open` (or no `close`) | `aget_connection()` / `aclose_connection()` from an async task |

  Each exception takes the offending name (task name, runner class name, plugin name) so the
  message is specific. The follow-up-issue reference lives in one module constant,
  `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE = "https://github.com/nornir-automation/nornir/issues/1085"`,
  swapped for the follow-up's URL once it exists (a merge precondition per the spec).
- **Rationale**: one distinct class per wrong combination (spec requirement) plus a base so an
  application can catch the whole family. The `*Error` suffix matches `NornirExecutionError`;
  the ruff ignore `N818` means older names without the suffix are tolerated but new ones follow
  PEP 8.
- **Alternatives**: the proposal's `SyncTaskOnAsyncRunnerError` / `AsyncTaskOnSyncRunnerError`
  — rejected because `Task.run(async_subtask)` inside an async task is *on* the async runner,
  so "runner" in the name would be false; "Run" describes the path, not the plugin.

## R5. Sharing result and failure semantics between `start`/`run` and `astart`/`arun`

- **Decision**: refactor `Task.start` into three private helpers and reuse them from `astart`:
  - `_begin(host)`: sets `self.host`, emits `task_instance_started` or
    `subtask_instance_started`, logs.
  - `_result_from_exception(host, exc)`: the existing two `except` branches
    (`NornirSubTaskError` → `Result(result=str(e), failed=True)`, other `Exception` →
    `Result(result=traceback.format_exc(), failed=True)`), returning the `Result`.
  - `_finish(host, r)`: the existing tail — coerce a non-`Result` return into `Result`, set
    `name` and severity, `results.insert(0, r)`, emit `*_instance_completed`, return
    `self.results`.

  `start` becomes `_begin`; `try: r = self.task(...)`; `except Exception as e: r = _result_from_exception(...)`; `_finish`.
  `astart` is the same shape with `r = await self.task(...)`.
  Likewise `Task.run` splits into `_new_subtask(task, kwargs) -> Task` and
  `_record_subtask(run_task, r) -> MultiResult` (append to `self.results`, raise
  `NornirSubTaskError` if failed); `run` calls `start` between them, `arun` awaits `astart`.
- **Rationale**: FR-008 says "same result-tree and failure semantics"; sharing the code is the
  only way that stays true over time. `except Exception` (not `BaseException`) is kept, so
  `asyncio.CancelledError` (a `BaseException` since 3.8) propagates out of `astart` without
  recording anything (FR-016). The refactor also keeps `start`'s mccabe complexity under the
  configured 10.
- **Alternatives**: duplicating the body into `astart` (rejected: drift); a single
  `_execute(call)` taking a callable that may or may not be awaited (rejected: obscures the
  traceback and the `pdb` step-through, Principle I).

## R6. Runner algorithm, concurrency bound, cancellation

- **Decision**: `AsyncioRunner.arun`:
  1. `semaphore = asyncio.Semaphore(self.num_workers)` created per call (bound to the running
     loop lazily; per-call so one runner instance can serve several loops over its life).
  2. For each host, `asyncio.ensure_future(_run_host(host))` where `_run_host` does
     `async with semaphore: return await task.copy().astart(host)`.
  3. `results = await asyncio.gather(*futures)`; build `AggregatedResult(task.name)` keyed by
     `host.name` in the original host order (gather preserves order, matching `ThreadedRunner`).
  4. `except BaseException: cancel every future; await asyncio.gather(*futures, return_exceptions=True); raise`
     — cancel-and-drain so that when the caller observes `CancelledError`, no host coroutine is
     still pending (FR-016, US4 scenario 2).
- **Rationale**: `asyncio.gather` + `Semaphore` is the simplest construct available on 3.10
  (`TaskGroup` is 3.11+, and its "cancel siblings on first exception" semantics would be wrong:
  `astart` never raises for task failures, so a raising child is always a `BaseException` such as
  cancellation). The semaphore protects devices, not the client, so the default stays 20.
- **Alternatives**: `TaskGroup` (3.11+); a bounded worker pool draining a queue (more code, same
  behaviour); `asyncio.wait` (no ordering guarantee without extra bookkeeping).
- **Properties that fall out**: zero hosts → empty `AggregatedResult`, the existing warning in
  `Nornir` still logs; `num_workers` > host count → all hosts in flight; thread count unchanged
  (no executor is ever created).

## R7. `Nornir.arun` and sharing with `Nornir.run`

- **Decision**: extract `Nornir.run`'s body into `_prepare_run(task, name, kwargs) -> tuple[Task, list[Host]]`
  (build the `Task`, emit `task_started`, select hosts by `on_good`/`on_failed`, log) and
  `_finish_run(run_task, result, raise_on_error) -> AggregatedResult` (apply `raise_on_error`,
  update `data.failed_hosts`, emit `task_completed`). `run` = validate task is not a coroutine
  function → `_prepare_run` → `self.runner.run(...)` → `_finish_run`. `arun` = validate task is a
  coroutine function → validate runner via `_is_async_runner` → `_prepare_run` →
  `await runner.arun(...)` → `_finish_run`. `arun` is typed
  `task: Callable[..., Coroutine[Any, Any, Any]]`.
  `aclose_connections(on_good=True, on_failed=False)` runs an `async def` task that awaits
  `task.host.aclose_connections()` through `arun`. `__aenter__` returns `self`; `__aexit__`
  awaits `aclose_connections(on_good=True, on_failed=True)`.
- **Rationale**: FR-002/FR-003 (same arguments, same `failed_hosts` and `raise_on_error`
  handling) are guaranteed by construction; validation before `task_started` gives the "before
  any host starts" guarantee for the async entry point.
- **Alternatives**: a `Callable[..., Awaitable[Any]]` annotation (rejected: a `def` returning an
  awaitable would type-check but fail the runtime check; `Coroutine` is what `async def` is).

## R8. Async connection plugin contract and structural detection

- **Decision**: `AsyncConnectionPlugin` Protocol in `nornir/core/plugins/connections.py` with
  `async def aopen(hostname, username, password, port, platform, extras=None, configuration=None) -> None`,
  `async def aclose() -> None`, and the `connection` property; parameters identical to `open`.
  Registration reuses `ConnectionPluginRegister`, whose type parameter stays
  `type[ConnectionPlugin]` (a plugin implementing only the async contract is still accepted at
  runtime; the registry does not type-check what entry points hand it). Detection is by two
  private `TypeGuard` helpers in `nornir/core/inventory.py`:
  `_has_async_members(plugin) -> TypeGuard[AsyncConnectionPlugin]` checks
  `inspect.iscoroutinefunction(getattr(plugin, "aopen", None))`;
  `_has_sync_members(plugin) -> TypeGuard[ConnectionPlugin]` checks
  `callable(getattr(plugin, "open", None))`. `connection` is deliberately not probed.
- **Rationale**: the spec's assumption is structural detection; probing `open`/`aopen` only
  avoids the false negative for plugins that create `connection` lazily inside `open()`.
- **Alternatives**: `@runtime_checkable` protocols (rejected, see R2); a class attribute flag
  such as `is_async = True` (rejected: SC-005 requires adding exactly two methods and nothing
  else).

## R9. `Host` async connection methods and the connection cache

- **Decision**: add `aget_connection`, `aopen_connection`, `aclose_connection`,
  `aclose_connections` to `Host`, over the same `self.connections` dict keyed by name.
  - `aopen_connection`: raise `ConnectionAlreadyOpen` if the name is in `connections` **or** in a
    new private slot `_opening: set[str]`; instantiate the plugin; raise
    `ConnectionPluginNotAsyncError` if `_has_async_members` is false; add the name to
    `_opening`; `await conn.aopen(...)` in a `try/finally` that discards the name from
    `_opening`; on success store in `connections`.
  - `aget_connection`: if the name is in `_opening` raise `ConnectionAlreadyOpen` (the
    "concurrent fan-out inside one task" edge case: the second call raises rather than opening a
    second connection); if absent, `await aopen_connection(...)`; return
    `connections[name].connection`. A connection opened by the sync path is found in the same
    dict and returned without reopening (US2 scenario 4).
  - `aclose_connection(name)`: pop; `await aclose()` if the plugin has async members, else
    `close()`. `aclose_connections()`: iterate over a snapshot of the keys and await
    `aclose_connection` for each (FR-014).
  - Sync side: `open_connection` raises `ConnectionPluginNotSyncError` when `_has_sync_members`
    is false (today it would be an `AttributeError`); `close_connection` raises the same when the
    stored plugin has no `close`. `close_connections` is otherwise unchanged.
- **Rationale**: the cache must stay shared and keyed by name (FR-012). An `await` sits between
  the cache lookup and the insertion, so a pending-open marker is the only way to make the
  concurrent case raise instead of leaking a connection. A private `__slots__` entry is not
  public API; `Group` inherits it; pickling of slotted objects skips unset slots and
  `tests/core/test_pickle.py` covers the round trip.
- **Alternatives**: inserting the plugin object into `connections` before awaiting `aopen`
  (rejected: a concurrent `aget_connection` would return a not-yet-open connection; and
  `close_connections` would see a half-open entry); a per-host `asyncio.Lock` (rejected: the
  proposal chose "raise" over "wait", and a lock bound to one loop on a long-lived `Host` is a
  trap).

## R10. Driving the event loop in tests

- **Decision**: no new development dependency. Each async test is a normal `def test_...` that
  calls `asyncio.run(main())` on a local coroutine (or a tiny `run()` helper in the test module).
  The session-scoped `nornir` fixture and `reset_data` autouse fixture from `tests/conftest.py`
  are reused unchanged.
- **Rationale**: `pytest-asyncio` and `anyio`'s pytest plugin are not in `[dependency-groups]`
  (anyio appears in `uv.lock` only transitively). `asyncio.run()` creates and closes a fresh loop
  per test, which also mirrors how an application would call `arun`, and it needs no
  `asyncio_mode` configuration that changes across plugin versions.
- **Alternatives**: `pytest-asyncio` (a dev dependency would be allowed with maintainer approval
  in the PR, but it is not needed).

## R11. Performance criteria as tests

- **Decision**: SC-003 becomes a test: 1,000 hosts built in memory, task awaits
  `asyncio.sleep(0.1)`, `AsyncioRunner(num_workers=1000)`, assert wall clock < 2 s and
  `threading.active_count()` equal before and after. SC-002 becomes a test: 100 hosts with the
  same task and a heartbeat coroutine sleeping 10 ms in a loop while recording the maximum gap
  with `time.monotonic()`; assert the maximum gap < 50 ms. Both live in
  `tests/plugins/runners/test_asyncio.py` and are plain tests, not skipped anywhere.
- **Rationale**: the spec makes them measurable outcomes. The SC-003 bound is 20× the work, so
  it is robust on CI. SC-002's 50 ms bound clears Windows' ~15.6 ms timer granularity.
- **Risk**: a heavily loaded CI runner could produce a > 50 ms scheduling gap unrelated to the
  runner. If that happens the assertion is loosened with a comment, never skipped or removed.
- **Alternatives**: counting heartbeat ticks instead of measuring gaps (weaker: it does not
  detect a single long stall).

## R12. `AsyncEcho` fixture and the echo server

- **Decision**: `tests/plugins/connections/async_echo.py` defines `AsyncEcho`, a fully typed,
  standard-library-only plugin implementing only the async contract: `aopen` does
  `asyncio.open_connection(hostname, port)` and stores an `EchoConnection` object exposing
  `async def send(payload: bytes) -> bytes` (write, drain, `readexactly`); `aclose` closes the
  writer, awaits `wait_closed()`, and is idempotent. `tests/plugins/connections/test_async_echo.py`
  starts an echo server with `asyncio.start_server(handler, "127.0.0.1", 0)` inside the test's
  `asyncio.run()` scope, reads the port from `server.sockets[0].getsockname()[1]`, registers the
  plugin under `"async_echo"`, and drives it through `nr.arun` with `num_workers` small enough
  to exercise the semaphore. The module is what the docs `literalinclude`, so it carries no
  test-only imports.
- **Rationale**: FR-018 (stdlib only, test-only, all platforms). `uv_build` with
  `module-root = ""` packages `nornir/` only, so nothing under `tests/` ships in the wheel.
  Ephemeral ports avoid collisions in parallel CI.
- **Alternatives**: a UNIX-socket echo (not portable to Windows); a fake in-memory transport
  (does not exercise real `asyncio` streams, weaker as a template for plugin authors).

## R13. Documentation shape

- **Decision**:
  - `docs/howto/asyncio_runner.ipynb` with its own `docs/howto/asyncio_runner/config.yaml`
    (`runner: plugin: asyncio`) and a three-host inventory. Cells use top-level `await`
    (supported by ipykernel, which is what nbval runs). The named-error cells wrap the call in
    `try/except` and `print(type(exc).__name__, exc)` so the stored output is deterministic and
    survives `docs/nbval_sanitize.cfg` unchanged. No timing is printed.
  - `docs/howto/writing_async_connection_plugins.rst`: the plugin-author page; explains the
    sibling contract, `literalinclude`s `../../tests/plugins/connections/async_echo.py`, states
    the two rules (`aopen`/`aclose` must not block; `aclose` must be safe to call twice), and
    shows how a plugin implementing both contracts is registered once.
  - `docs/plugins/index.rst` (Connections section mentions `AsyncConnectionPlugin`; the Runners
    automodule already documents `AsyncioRunner`), `docs/plugins/execution_model.rst` (one
    paragraph), `docs/configuration/parameters.rst` (list `serial`, `threaded`, `asyncio`).
  - `CHANGELOG.rst`: a `3.7.0 - unreleased` section (date set at release, as
    `docs: set the 3.6.0 changelog date` did last time) listing the feature with `#1085` and the
    one sync-path behaviour change.
- **Rationale**: FR-019 and Principle V. The howto toctree globs `*`, so new pages appear
  without editing `docs/howto/index.rst`.
- **Alternatives**: letting the error cells raise (rejected: IPython's traceback format is not
  covered by the sanitizer and varies across versions).

## R14. Python version and platform constraints

- **Decision**: only APIs available on 3.10 are used: `asyncio.Semaphore`, `asyncio.gather`,
  `asyncio.ensure_future`, `asyncio.run`, `asyncio.open_connection`/`start_server`,
  `inspect.iscoroutinefunction`, `typing.TypeGuard`. Nothing platform-specific.
- **Rationale**: Principle IV; `PYTHON:=3.10` in the Makefile is the Docker default and
  `python_version = "3.10"` in `[tool.mypy]` is the type-check floor.

## R15. Lint and type-check constraints to design around

- `ruff` selects `ALL` with `preview = true`: the `ASYNC` rules apply (no blocking calls in
  `async def`, no `asyncio.sleep(0)` busy loops), mccabe max 10, `PLR` limits (11 args, 16
  branches). The `Task` refactor in R5 keeps `start`/`astart` within limits. `BLE001` is already
  ignored for `nornir/core/task.py` and `tests/**`, which is where the blind `except Exception`
  lives.
- `mypy` runs on `tests/` too: the fixture plugin, the echo server handler and every test
  coroutine carry full annotations.
- No new entries are added to either ignore list; if one becomes unavoidable it carries the
  reason as a comment (Principle III).

## R16. Things confirmed not to need change

- `nornir/init_nornir.py::load_runner` — instantiates by registry name with the config options.
- `nornir/core/configuration.py::RunnerConfig` — default stays `threaded`.
- `docs/api/nornir/**` — no module added or removed, so `docs/build_api.sh` output is unchanged.
- `docs/nbval_sanitize.cfg` — sufficient given R13.
- Existing `ConnectionPlugin`, `RunnerPlugin`, `Processor` Protocols — untouched.
