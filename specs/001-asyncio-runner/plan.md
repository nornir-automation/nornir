# Implementation Plan: Asyncio Runner

**Branch**: `dga/feat-async-spplb` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-asyncio-runner/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add opt-in native `asyncio` support next to the threaded runner: an in-tree `AsyncioRunner`
registered as `asyncio`, `await nr.arun(task)` / `async with nr:` / `await nr.aclose_connections()`
on `Nornir`, `astart` / `arun` on `Task`, an optional sibling `AsyncConnectionPlugin` protocol with
the matching `a*` connection methods on `Host`, and one named error per wrong sync/async
combination. Nothing changes unless the `asyncio` runner is selected.

Technical approach: the runner is a semaphore-bounded fan-out of `task.copy().astart(host)`
coroutines on the caller's event loop, with cancel-and-drain on cancellation. `Task.start`/`run`
and `Task.astart`/`arun` share one set of private helpers so result and failure semantics are
written once. Sync/async capability of runners and connection plugins is detected structurally
(presence of `arun` / `aopen`) through `TypeGuard` helpers, matching the structural `Protocol`
design of the existing contracts. No new runtime dependency; the `AsyncEcho` reference plugin
lives under `tests/` and is included in the docs by `literalinclude`.

## Technical Context

**Language/Version**: Python 3.10 through 3.14 (3.10 is the floor: no `asyncio.TaskGroup`,
no `asyncio.timeout`; `asyncio.Semaphore`, `asyncio.gather`, `inspect.iscoroutinefunction`,
`typing.TypeGuard` are all available)

**Primary Dependencies**: standard library only (`asyncio`, `inspect`, `typing`). Runtime
dependencies stay at `ruamel.yaml`. No new development dependency either: async tests drive the
loop with `asyncio.run()` (see research R10).

**Storage**: N/A

**Testing**: pytest (`make pytest`), mypy on `nornir` and `tests` (`make mypy`), ruff, nbval on
`docs/howto/` and `docs/tutorial/`, Sphinx (`make docs`). Async tests call `asyncio.run()` inside
ordinary synchronous test functions.

**Target Platform**: Linux, macOS, Windows, all first-class. The `AsyncEcho` fixture uses
`asyncio.start_server` / `asyncio.open_connection` on `127.0.0.1` with an ephemeral port, which the
default event loop supports on all three (Proactor loop on Windows).

**Project Type**: library (pure Python, plugin-extensible)

**Performance Goals**: SC-002 (a sibling coroutine is never starved > 50 ms during a 100-host
run of 100 ms simulated I/O) and SC-003 (1,000 hosts × 100 ms with `num_workers=1000` completes
in < 2 s wall clock, thread count unchanged).

**Constraints**: additive only (FR-020): no existing signature, protocol member, default or
entry-point name changes. No concurrency logic outside the runner. Debuggable with stock Python
tooling (a breakpoint in an `async def` task pauses the run; a failed host's traceback contains
the user's task code).

**Scale/Scope**: five source files touched (`nornir/core/__init__.py`, `nornir/core/task.py`,
`nornir/core/inventory.py`, `nornir/core/exceptions.py`, `nornir/core/plugins/connections.py`,
`nornir/core/plugins/runners.py`, `nornir/plugins/runners/__init__.py`, `pyproject.toml`), one
new test fixture plugin, five new test modules, one notebook, one prose page, one changelog entry.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-research | Post-design |
|---|---|---|---|
| I. Python-First, No DSL | Feature is plain Python objects/functions; no DSL; `pdb` in an `async def` task pauses the run; failed-host tracebacks point at user code | PASS: `async def` tasks are ordinary coroutines called directly by `Task.astart`; the traceback is captured with `traceback.format_exc()` exactly as in `start` | PASS: confirmed in design; `astart` awaits `self.task(self, **params)` with no wrapper layer |
| II. Thin Core, Capability at the Edge | No new runtime dependency; a new in-tree plugin needs maintainer approval; anything device-specific is out of tree | PASS with approval: `AsyncioRunner` is a *runner* (concurrency is core-owned) and the spec records maintainer approval for it as an in-tree plugin; `AsyncEcho` stays in `tests/` and is not packaged (`uv_build`, `module-root = ""` packages only `nornir/`) | PASS: the approval must be restated in the PR description |
| III. Typed and Statically Verified | Complete annotations, mypy strict passes, no new `# type: ignore` / `# noqa` without a reason | PASS: structural detection uses `typing.TypeGuard` helpers, so no casts or ignores are needed | PASS: `tests/` are type-checked too; the fixture plugin and test modules carry full annotations |
| IV. Tested Across the Whole Support Matrix | Tests accompany the change; pass on 3.10–3.14 and Linux/macOS/Windows; nothing platform-specific in core | PASS: no platform-specific code; the echo fixture runs on all three platforms | PASS with a noted risk: the two timing-based tests (SC-002, SC-003) have generous margins; if CI shows flakiness the bound is loosened, not the test skipped |
| V. Executable, Current Documentation | `make docs` and `make nbval` pass; user-visible change updates `docs/` and `CHANGELOG.rst`; notebook output is real | PASS: one executed how-to notebook, one prose page, changelog entry | PASS: the notebook prints the named errors from `except` blocks so the stored output is deterministic under nbval |
| VI. Stable Public API, Semantic Versioning | No signature change on existing public members or Protocols; additive only; ships in a MINOR | PASS: `ConnectionPlugin` and `RunnerPlugin` untouched; new members and two new sibling Protocols only | PASS: one behavioural change on the sync path (an `async def` task on a sync runner now raises instead of recording a coroutine as success) affects only input that was already incorrect; called out in the changelog |

**Gate result**: PASS (pre-research and post-design). No Complexity Tracking entries are needed.

### Deviations from the specification (not from the constitution)

- **SC-001 cannot hold literally.** `tests/core/test_registered_plugins.py::test_registered_runners`
  asserts that the auto-registered runner set is exactly `{serial, threaded}`. Registering
  `asyncio` (FR-001) makes that assertion fail. The test enumerates the in-tree registry rather
  than testing behaviour, so the plan updates that one assertion to include `asyncio` and asks
  for SC-001 to be reworded to "passes unmodified except for the registry-inventory assertion
  that enumerates the in-tree runners". No other pre-existing test changes.
- **`nr.run()` on the `asyncio` runner raises after `task_started`.** `RunnerNotSyncError` comes
  from `AsyncioRunner.run()`, which `Nornir.run()` reaches only after emitting `task_started`.
  `task_started` is not a per-host event, so SC-004 ("before a single per-host event") holds, but
  processors see a `task_started` with no matching `task_completed` in this error case. The mirror
  case (`nr.arun()` on a sync runner) is detected structurally in `Nornir.arun()` before any event.
  The asymmetry is accepted because the only way to remove it is a runner-kind marker on the
  `RunnerPlugin` contract, which FR-020 forbids (see research R2).

## Project Structure

### Documentation (this feature)

```text
specs/001-asyncio-runner/
├── plan.md              # This file
├── spec.md              # Feature specification (input)
├── research.md          # Phase 0 output: decisions R1–R16
├── data-model.md        # Phase 1 output: entities, state, validation
├── quickstart.md        # Phase 1 output: end-to-end validation guide
├── contracts/
│   ├── protocols.py     # AsyncConnectionPlugin / AsyncRunnerPlugin as typed stubs
│   ├── entry-points.md  # Nornir / Task / Host async members and their semantics
│   └── errors.md        # The named-error matrix (which surface raises what, pointing where)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already present)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
nornir/
├── core/
│   ├── __init__.py                 # Nornir.arun, aclose_connections, __aenter__/__aexit__;
│   │                               #   run() refactored onto shared _prepare_run/_finish_run
│   ├── task.py                     # Task.astart, Task.arun; start/run refactored onto shared
│   │                               #   _begin/_result_from_exception/_finish helpers;
│   │                               #   _is_coroutine_function helper
│   ├── inventory.py                # Host.aget_connection, aopen_connection, aclose_connection,
│   │                               #   aclose_connections; private _opening slot; sync
│   │                               #   open/close gain the "plugin has no sync members" check
│   ├── exceptions.py               # SyncAsyncMismatchError + six named subclasses
│   └── plugins/
│       ├── connections.py          # AsyncConnectionPlugin Protocol (sibling, optional)
│       └── runners.py              # AsyncRunnerPlugin Protocol (sibling, optional)
└── plugins/
    └── runners/__init__.py         # AsyncioRunner (num_workers=20; run() raises, arun() runs)

pyproject.toml                      # [project.entry-points."nornir.plugins.runners"] asyncio = ...

tests/
├── core/
│   ├── test_registered_plugins.py  # ONLY pre-existing test touched: add "asyncio" to the set
│   ├── test_async_run.py           # Nornir.arun semantics, failed_hosts, raise_on_error,
│   │                               #   processor event order, async with, aclose_connections,
│   │                               #   the seven-surface error matrix
│   ├── test_async_tasks.py         # Task.arun/astart, subtask failure semantics, task.run()
│   │                               #   inline inside async, task.run(async def) error
│   └── test_async_connections.py   # Host a* connection methods with sync/async/both dummies,
│                                   #   mixed cleanup, cache shared by name, concurrent aget
└── plugins/
    ├── connections/
    │   ├── __init__.py
    │   ├── async_echo.py           # AsyncEcho fixture plugin (stdlib only) — literalincluded
    │   └── test_async_echo.py      # echo server fixture + end-to-end async connection path
    └── runners/
        ├── __init__.py
        └── test_asyncio.py         # concurrency bound, host order, failures, cancellation,
                                    #   zero hosts, num_workers > hosts, SC-002, SC-003

docs/
├── howto/
│   ├── asyncio_runner.ipynb        # executed how-to: runner selection, async task, arun,
│   │                               #   async with, named errors printed as real output
│   ├── asyncio_runner/
│   │   ├── config.yaml             # runner: plugin: asyncio
│   │   └── inventory/{hosts,groups,defaults}.yaml
│   └── writing_async_connection_plugins.rst   # plugin-author page; literalinclude of the
│                                              #   AsyncEcho source; the two async-member rules
├── plugins/
│   ├── index.rst                   # Connections: mention AsyncConnectionPlugin; Runners auto-
│   │                               #   documents AsyncioRunner via the existing automodule
│   └── execution_model.rst         # one paragraph on the asyncio execution model
└── configuration/parameters.rst    # runner.plugin: list the three in-tree names

CHANGELOG.rst                       # new 3.7.0 section with the feature and the one sync-path change
```

**Structure Decision**: single library project, existing layout. Runner tests go under
`tests/plugins/runners/` to mirror the package layout as AGENTS.md prescribes; the existing
`test_serial.py`/`test_threaded.py` live under `tests/plugins/processors/` for historical reasons
and are deliberately left where they are (FR-020). No module is added or removed under `nornir/`,
so `docs/api/nornir/**` does not need regenerating; autodoc picks up the new classes through the
existing `.rst` files.

## Complexity Tracking

No constitution violations to justify. The two specification deviations are recorded above.

## Phase 0: Research

Complete — see [research.md](research.md). All Technical Context items resolved; no
NEEDS CLARIFICATION markers remain.

## Phase 1: Design & Contracts

Complete — see [data-model.md](data-model.md), [contracts/](contracts/), and
[quickstart.md](quickstart.md).

## Precondition for merge (from the spec's Assumptions)

The follow-up issue on synchronous tasks in async runs must be opened before this feature merges;
its number replaces `#1085` in the single `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE` constant that the
`SyncTaskOnAsyncRunError` message reads (research R4).
