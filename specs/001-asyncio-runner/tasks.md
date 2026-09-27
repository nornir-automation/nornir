---
description: "Implementation tasks for the asyncio runner and capability-aware connection plugins"
---

# Tasks: Asyncio Runner

**Updated**: 2026-09-13
**Input**: `specs/001-asyncio-runner/`
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md)
(R1–R14), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md).

**Tests**: Required by the specification and constitution. Write new behavior tests before
implementation and observe the missing behavior where applicable. Broader regression tests
may already pass when earlier phases implemented their behavior; never manufacture a failure.
Use ordinary fully typed pytest functions driving asyncio.run, without new dependencies.

**Organization**: Four user stories, all shipped together. Checkpoints validate increments;
they are not separate releases. T001–T003 preserve completion recorded in the previous list.
Scaffolding files were confirmed present; historical baseline results are not reasserted as
current evidence. T004 explicitly refreshes that baseline before implementation.

## Format and conventions

- Tasks use checkbox, sequential ID, optional [P], required story label in story phases,
  and exact repository-relative paths. Completed historical tasks retain checked boxes.
- [P] marks independent file streams after stated prerequisites. It never permits two
  concurrent writers to one file or execution before a dependency is ready.
- Existing public signatures/types and the legacy registry remain unchanged. The only
  permitted pre-existing test edit is the runner assertion/import in T017.
- Tests reset/snapshot both connection registries within new local fixtures; preserve
  existing test fixtures and module behavior. No unchecked suppression or dependency additions.
- Commands/evidence go in `specs/001-asyncio-runner/validation.md` during implementation.
  Do not mark a gate complete without actual results. Commit/push only when explicitly requested.

## Phase 1: Setup

**Goal**: Retain scaffolding and establish fresh execution evidence.

- [X] T001 [P] Create `tests/plugins/runners/__init__.py` as an empty package marker mirroring the runner package (retained completed task).
- [X] T002 [P] Create `tests/plugins/connections/__init__.py` as an empty package marker for connection fixtures and integration tests (retained completed task).
- [X] T003 Run `make pytest` and `make mypy` from `Makefile` to record the original green baseline before core changes (historical completion retained; T004 refreshes evidence).
- [X] T004 Verify the environment with `uv sync --locked`, then run `make pytest` and `make mypy` from `Makefile` before editing core code; create `specs/001-asyncio-runner/validation.md` with interpreter/platform, commands, outcomes, and any baseline blockers; retain dependency choices in `pyproject.toml` and `uv.lock`.

## Phase 2: Foundational prerequisites

**Goal**: Shared contracts/errors and behavior-preserving execution bookkeeping. All user
stories depend on the T011 checkpoint.

- [X] T005 [P] Add the six mismatch errors under `SyncAsyncMismatchError`, separate `ConnectionPluginAmbiguousError(connection_name)` and `ConnectionPluginContractError(connection_name, reason)`, and `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE` to `nornir/core/exceptions.py` following `specs/001-asyncio-runner/contracts/errors.md`; preserve existing exception definitions and use the temporary #1085 URL until T056.
- [X] T006 [P] Add private coroutine detection and safe diagnostic-name helpers in `nornir/core/task.py`: support native async functions, partials and async callable instances; derive mismatch names from an explicit name, string `__name__`, or callable type name; preserve existing Task naming so unnamed callable forms still require `name=` (research R8).
- [X] T007 [P] Add `AsyncRunnerPlugin` to `nornir/core/plugins/runners.py` with the signature in `specs/001-asyncio-runner/contracts/protocols.py`; keep `RunnerPlugin` and `RunnersPluginRegister` unchanged.
- [X] T008 After T006, refactor `Task.start` in `nornir/core/task.py` onto private begin, exception-to-result, and finish helpers, retaining result coercion/naming/severity, user tracebacks, event order, and `except Exception` rather than `BaseException`; keep direct invocation of the original callable visible (research R8).
- [X] T009 After T008, refactor `Task.run` in `nornir/core/task.py` onto private child construction and result-recording helpers, preserving host validation, inherited severity, parent linkage, result insertion, and `NornirSubTaskError` semantics.
- [X] T010 [P] Refactor `Nornir.run` in `nornir/core/__init__.py` onto `_prepare_run(task, name, kwargs, on_good, on_failed)` and a shared finalizer; explicitly pass both selection flags, preserve good/failed host ordering, zero-host warning, raise_on_error resolution, failed_hosts mutation, and global completion order.
- [X] T011 Run `make pytest`, `make mypy`, and `make ruff` from `Makefile` after T005–T010; require the entire pre-existing suite to pass unmodified at this stage and record results in `specs/001-asyncio-runner/validation.md` (FR-020).

**Checkpoint**: Synchronous execution remains compatible; shared helpers, errors, and runner
contract are available. T010 may run alongside the sequential T006 → T008 → T009 stream.

## Phase 3: US1 — Run async tasks from an event loop (P1)

**Goal**: Async tasks and subtasks on the caller's loop, with bounded concurrency and
existing result/failure semantics.

**Independent test**: An in-memory inventory and simulated async I/O produce one result
per selected host, preserve event ordering constraints, and keep a sibling heartbeat responsive.
No connection plugin is required.

### Tests

- [X] T012 [P] [US1] Create `tests/plugins/runners/test_asyncio.py` with typed tests for ordered host results, independent host failure, concurrency bound, default 20 workers, worker counts above inventory size, empty host input, TypeError for boolean/non-integer counts, ValueError for zero/negative counts, sync `run` rejection, and a basic cancellation/drain test; use barriers/counters rather than scheduling sleeps for coordination (FR-001/004, research R9).
- [X] T013 [US1] After T012, add SC-002/003 tests to `tests/plugins/runners/test_asyncio.py`: 100 hosts with 100 ms I/O and heartbeat maximum gap at most 50 ms, and 1,000 hosts with 1,000 workers and 100 ms I/O under two seconds with unchanged live thread count; exclude inventory construction from timing, establish heartbeat readiness, and include the final active-run interval; never loosen bounds to mask failures (research R11).
- [X] T014 [P] [US1] Create `tests/core/test_async_run.py` with an independent local recording processor and tests for aggregate shape, InitNornir configuration/with_runner selection, task/name/kwargs, named partial/async-callable tasks, all four on_good/on_failed combinations, good/failed ordering, default/configured/overridden raise_on_error, failed-host reuse/skipping, and zero-host warning; assert global/per-host partial event ordering and arguments while permitting cross-host interleaving (FR-002/003/017).
- [X] T015 [US1] After T014, add top-level mismatch tests to `tests/core/test_async_run.py` for sync tasks on async arun, async tasks on serial and threaded run, and incompatible runner selection; assert named errors/message alternatives, safe diagnostics for unnamed callable forms, follow-up URL, and no host events; allow global task_started before AsyncioRunner.run rejects (FR-005/006, SC-004).
- [X] T016 [P] [US1] Create `tests/core/test_async_tasks.py` with async child success/failure and nested-result/event tests, inline sync children, both child mismatch directions, no child result/events on rejection, normal failed-parent conversion when uncaught, explicit names for partial/callable forms, and user-function source/name in tracebacks (FR-008–FR-010, Constitution I).
- [X] T017 [P] [US1] Update only the runner-registry assertion and import in `tests/core/test_registered_plugins.py` to include `"asyncio": AsyncioRunner`, the explicit FR-020/SC-001 exception; no other existing tests are modified.

### Implementation

- [X] T018 [US1] Implement `Task.astart(host)` in `nornir/core/task.py` using the shared helpers around a direct await of the original user callable; preserve ordinary exception-to-result handling and let BaseException escape without recording cancellation results.
- [X] T019 [US1] After T018, implement `Task.arun` and the synchronous Task.run mismatch guard in `nornir/core/task.py`; validate before child construction/execution events, reuse shared child bookkeeping, and retain inline synchronous children and explicit naming rules.
- [X] T020 [US1] Add private structural runner narrowing and the Nornir.run coroutine-task guard to `nornir/core/__init__.py`, using the task helpers before preparation and preserving existing public annotations.
- [X] T021 [US1] After T020, implement `Nornir.arun` in `nornir/core/__init__.py` with the exact new signature in `specs/001-asyncio-runner/contracts/entry-points.md`: task-kind check, runner check, explicit selection inputs to preparation, await runner, then existing finalization.
- [X] T022 [US1] Implement `AsyncioRunner` in `nornir/plugins/runners/__init__.py`: positive non-boolean worker validation, per-invocation semaphore, one copied Task per host, ordered gather, and unconditional sync run mismatch; wait for the initial aggregate without propagating caller cancellation, explicitly cancel unfinished children once on BaseException, shield/re-await draining through repeated caller cancellation, retrieve aggregate exceptions, and re-raise only after owned work is drained (research R1/R9). Cancellation correctness is required here, not deferred to US4.
- [X] T023 [US1] After T022, register `asyncio = "nornir.plugins.runners:AsyncioRunner"` under the existing runner entry-point group in `pyproject.toml`; refresh package installation with `uv sync --locked`, updating `uv.lock` with uv only if package metadata requires it while retaining dependency choices; verify selection through InitNornir configuration and with_runner using `tests/core/test_async_run.py`.
- [X] T024 [US1] Run `make pytest ARGS="tests/plugins/runners tests/core/test_async_run.py tests/core/test_async_tasks.py tests/core/test_registered_plugins.py"`, `make mypy`, and `make ruff` from `Makefile`; resolve failures, manually verify a debugger enters the original async task, and record evidence in `specs/001-asyncio-runner/validation.md`.

**Checkpoint**: US1 is independently demonstrable. Async dispatch includes cancellation
ownership; US4 will exercise more demanding cleanup and cancellation cases.

## Phase 4: US2 — Register capability-aware connection plugins (P1)

**Goal**: New generic contract and isolated registry for sync, asyncio, or both; typed
Host storage, capability-based access, legacy coexistence, and portable AsyncEcho.

**Independent test**: All capability combinations work through their declared paths;
AsyncEcho sends/receives real bytes through a local server and uses Host-level cleanup.
Nornir async cleanup is not used until Phase 5.

### Tests

- [X] T025 [P] [US2] Create `tests/core/test_capability_plugins.py` with fully typed structural author fixtures for the base/sync/async/dual protocols, including an async-only class with no sync stubs; test single programmatic registration, cold-start registry isolation, same-registry idempotency, automatic discovery for all capability combinations, and InitNornir discovery alongside legacy plugins. Local fixtures must snapshot/restore both registries; prove sync/dual objects fit unchanged public sync types (FR-011/021, SC-005/007).
- [X] T026 [P] [US2] Create `tests/core/test_async_connections.py` with independent local typed legacy/sync/async/dual fixtures and Host lifecycle tests: parameter inheritance/explicit overrides/default_to_host_attributes, single opening/cache reuse, both dual-mode reuse directions, mode checks before cached and uncached returns, legacy extras remaining sync-only, both stores' cleanup, and public cache type/visibility expectations (FR-012–FR-014).
- [X] T027 [US2] After T025, extend `tests/core/test_capability_plugins.py` with get/open tests for cross-registry duplicate names in either discovery order, same-class duplicates, and duplicate introduction after caching; add malformed reporting method/results, empty/unknown capabilities, missing opening/closing operations for any declared mode, and undeclared extra methods; assert contract/ambiguity errors before I/O, no connection-property probing, and cleanup remains possible despite ambiguity (FR-022/023).
- [X] T028 [US2] After T026, extend `tests/core/test_async_connections.py` with pending-open rejection, failed-open reservation cleanup, cached origin after deregistration/replacement, identity-matched metadata after public-cache replacement, conflicting public/private entries, filtered Host sharing, empty-Host copy/pickle, and unchanged inventory dict/schema output; include retained async-close failures/retry, identity-safe removal, sync metadata removal on close failure, and fail-fast sync versus attempt-all async bulk cleanup.
- [X] T029 [P] [US2] Create `tests/plugins/connections/test_async_echo.py` with a typed loopback/ephemeral-port asyncio server fixture and a failing end-to-end test that registers AsyncEcho in the capability registry, runs per-host send/receive via Nornir.arun, verifies cached reuse, and closes through Host.aclose_connections; assert repeated plugin aclose is safe and server/handler resources are drained. Do not call the later Nornir.aclose_connections API (FR-018).

### Implementation

- [X] T030 [US2] Add ConnectionCapability, CapabilityConnectionPlugin, SyncCapabilityConnectionPlugin, AsyncCapabilityConnectionPlugin, and DualCapabilityConnectionPlugin to `nornir/core/plugins/connections.py` exactly as specified in `specs/001-asyncio-runner/contracts/protocols.py`; document no-argument/no-I/O construction, stable instance reporting, required operations per mode, native async operations, and dual transport reuse; leave the legacy protocol intact.
- [X] T031 [US2] After T030, add `CapabilityConnectionPluginRegister: PluginRegister[type[CapabilityConnectionPlugin]]` and `CAPABILITY_CONNECTIONS_PLUGIN_PATH = "nornir.plugins.capability_connections"` to `nornir/core/plugins/connections.py`; explicitly allocate this registry's own available dictionary without changing `nornir/core/plugins/register.py` or legacy registration behavior.
- [X] T032 [US2] After T031, add capability-registry auto-discovery beside legacy discovery in `nornir/init_nornir.py`, before inventory loading; keep direct Nornir construction behavior unchanged and retain the legacy discovery group.
- [X] T033 [US2] After T031, implement private capability validation, full sync/async/dual TypeGuard helpers, and cross-registry name resolution in `nornir/core/inventory.py`; honor declarations rather than incidental methods, validate all declared pairs before mode selection, avoid reading connection before open, reject current duplicates even on get cache hits, and preserve registry-independent cleanup and cached origin (contracts/errors.md precedence).
- [X] T034 [US2] After T033, add `_async_connections`, `_capability_connections`, and `_opening` private Host slots and immutable `_CapabilityConnectionState` in `nornir/core/inventory.py`; preserve public `connections: dict[str, ConnectionPlugin]`, store original plugin identity/declaration, classify untracked public entries as legacy, and reject cross-store conflicts; preserve inventory serialization and shared Host ownership.
- [X] T035 [US2] After T034, implement Host.aopen_connection and capability-aware synchronous opening in `nornir/core/inventory.py`; reuse parameter resolution, check both stores/reservations, validate before opening, reserve async names before suspension, publish metadata/cache only on success, and clear reservations in finally. Return the async facet from aopen and retain ConnectionPlugin return from sync open; place sync/dual instances in public storage and async-only instances privately.
- [X] T036 [US2] After T035, implement Host.aget_connection and capability-aware get_connection in `nornir/core/inventory.py`; check current registry ambiguity, pending state, and identity-matched cached capabilities before returning transport; reuse dual-mode connections without reopening and preserve entries on mismatch, deregistration, or class replacement.
- [X] T037 [US2] After T036, implement Host.aclose_connection and extend synchronous close_connection in `nornir/core/inventory.py`; use cached ownership independent of registries, prefer aclose for dual/async, retain async entries on failure/cancellation, identity-check removal after awaits, and preserve sync pop-before-close with matching metadata removal; reject sync mode mismatch before removing anything.
- [X] T038 [US2] After T037, implement Host.aclose_connections and capability-aware close_connections in `nornir/core/inventory.py`; snapshot both stores, keep sync bulk fail-fast including async-only mismatch, attempt every async bulk entry after ordinary errors then raise the first, and propagate cancellation immediately; document that callers serialize use/cleanup while a name closes.
- [X] T039 [US2] Implement the fully typed standard-library-only AsyncEcho fixture in `tests/plugins/connections/async_echo.py`: report frozenset({"asyncio"}), expose an async send(bytes) transport over StreamReader/StreamWriter, implement native aopen/aclose with the exact parameter contract, release partial resources on failed/cancelled open, and make close idempotent; no sync stubs or test-framework imports in the literalincluded module.
- [X] T040 [US2] Run `make pytest ARGS="tests/core/test_capability_plugins.py tests/core/test_async_connections.py tests/plugins/connections tests/core/test_connections.py tests/core/test_pickle.py"`, `make mypy`, and `make ruff` from `Makefile`; verify the new Host copy/pickle tests separately cover what the pre-existing MultiResult tests do not, and record results in `specs/001-asyncio-runner/validation.md`.

**Checkpoint**: Capability-aware registry and Host lifecycle work for every declared mode,
legacy plugins remain compatible, and AsyncEcho is validated without the Phase 5 API.

## Phase 5: US3 — Clean up in an async context (P2)

**Goal**: Nornir-level cleanup is visible to processors and honors host selection, with
async context exit closing good and failed hosts across both connection stores.

**Independent test**: Open mixed legacy/new-contract connections, mark a host failed,
exit async with, and assert all transports were closed with matching processor events.

### Tests

- [X] T041 [US3] Create Nornir cleanup/context tests in `tests/core/test_async_run.py` using local or completed Phase 4 fixtures: mixed legacy/sync/async/dual cleanup, good and failed hosts on async exit, all four selection combinations for explicit cleanup, processor visibility, sync cleanup/context mismatch on AsyncioRunner, and async cleanup/context mismatch on SerialRunner (FR-007/015).
- [X] T042 [US3] After T041, extend `tests/core/test_async_run.py` with failed async cleanup retaining connection state, failed-host bookkeeping under default raise_on_error, retry with on_failed=True, and propagation when raise_on_error is enabled; assert empty public connections alone is not treated as proof of complete async cleanup.

### Implementation

- [X] T043 [US3] Implement `Nornir.aclose_connections(on_good=True, on_failed=False)` in `nornir/core/__init__.py` as a typed async Host-cleanup task dispatched through arun; preserve processor visibility, selection flags, result/error bookkeeping, and the None return contract.
- [X] T044 [US3] After T043, implement fully typed async context entry/exit in `nornir/core/__init__.py`; return self on entry and clean with both host-selection flags true on exit; document retrying failed-host cleanup with on_failed=True or direct Host cleanup.
- [X] T045 [US3] Run `make pytest ARGS="tests/core/test_async_run.py tests/core/test_async_connections.py tests/plugins/connections"`, `make mypy`, and `make ruff` from `Makefile`; record US3 evidence in `specs/001-asyncio-runner/validation.md`.

## Phase 6: US4 — Cancel a run in progress (P3)

**Goal**: Prove the cancellation ownership introduced in US1 also holds with awaited
resource cleanup, queued hosts, repeated cancellation, and real connection opening.

**Independent test**: Cancel after a barrier confirms twenty active hosts and additional
waiters. Assert CancelledError, completed host cleanup, unchanged failed_hosts, no global
completion, and no runner-owned work remaining.

### Tests

- [X] T046 [P] [US4] Extend `tests/plugins/runners/test_asyncio.py` with deterministic cancellation tests: twenty active hosts plus semaphore waiters, a prompt child beside an awaited-finally child, repeated caller cancellation during draining, and aggregate exception retrieval; assert cleanup completes, cancellation propagates, failed_hosts is unchanged, no global completion occurs, and no owned task is pending; do not require rollback of previously observed events (FR-016).
- [X] T047 [P] [US4] Extend `tests/core/test_async_connections.py` with cancellation during aopen and aclose: partial resources released by the plugin, opening reservation cleared without publishing a cache entry, failed/cancelled async close retained for retry, successful retry removing matching state, and no stale metadata applied after replacement.
- [X] T048 [P] [US4] Extend `tests/plugins/connections/test_async_echo.py` with cancellation/error integration scenarios exercising partial transport opening and handler cleanup; assert sockets/writers and server tasks are closed or drained after completion on all supported platforms, with no external service dependency.

### Integration and validation

- [X] T049 [US4] Verify and, if the expanded tests expose gaps, correct cancellation/resource ownership in `nornir/plugins/runners/__init__.py`, `nornir/core/inventory.py`, and `tests/plugins/connections/async_echo.py` against `specs/001-asyncio-runner/contracts/entry-points.md`; preserve single child-cancellation ownership, shielded draining, exception retrieval, and cache/resource failure boundaries. Do not weaken tests or add workarounds that hide unfinished tasks.
- [X] T050 [US4] Run `make pytest ARGS="tests/plugins/runners tests/core/test_async_connections.py tests/plugins/connections"`, `make mypy`, and `make ruff` from `Makefile`; record cancellation evidence in `specs/001-asyncio-runner/validation.md`.

## Phase 7: Documentation and cross-cutting gates

- [X] T051 [P] Create `docs/howto/asyncio_runner/config.yaml` and `docs/howto/asyncio_runner/inventory/hosts.yaml`, `groups.yaml`, and `defaults.yaml` with a small inventory and asyncio runner selection; inventory paths must resolve from the notebook working directory `docs/howto/`.
- [X] T052 After T051, create and execute `docs/howto/asyncio_runner.ipynb` demonstrating runner selection, native async tasks/subtasks, arun, async with, genuine printed named mismatch errors, and explicit names for callable forms without __name__; explain inline synchronous subtasks and processor-hook blocking without fabricated timing/output. Store exactly the executed output (FR-019, SC-006).
- [X] T053 [P] Create `docs/howto/writing_capability_connection_plugins.rst` documenting the base and operation facets, stable no-I/O capability method, all three declarations, programmatic/discovered registration via `nornir.plugins.capability_connections`, legacy coexistence, duplicate-name policy, typed/public cache visibility, cross-mode reuse, cleanup retry, serialized use while closing, native async/idempotent-close/partial-open-cleanup rules; literalinclude `../../tests/plugins/connections/async_echo.py` as the runnable reference.
- [X] T054 [P] Update `docs/plugins/index.rst`, `docs/plugins/execution_model.rst`, and `docs/configuration/parameters.rst` to link the new guide/notebook, explain both registries and execution-mode capabilities, document synchronous processor blocking with #1090, and list asyncio runner options while preserving the threaded default.
- [X] T055 [P] Add an unreleased minor-release entry to `CHANGELOG.rst` citing #1085 and describing asyncio dispatch, capability-aware contract/registry, async cleanup, legacy compatibility, and named rejection of coroutine tasks on synchronous task entry points; do not invent a PR number.
- [ ] T056 Open the dedicated synchronous-tasks-in-async-runs follow-up issue described in `specs/001-asyncio-runner/spec.md`, replace the temporary URL in `nornir/core/exceptions.py`, and update any hard-coded expectation in `tests/core/test_async_run.py`; record the actual URL in `specs/001-asyncio-runner/validation.md` (merge prerequisite).
- [X] T057 Run `make nbval` and `make docs` from `Makefile` after documentation changes; inspect and retain legitimate generated changes under `docs/api/nornir/`, fix prose/include/link issues at their source, and re-execute changed notebooks rather than editing outputs by hand; record evidence in `specs/001-asyncio-runner/validation.md`.
- [X] T058 Build the distribution with `uv build` using `pyproject.toml`, run the existing wheel importability validation in `tests/wheel_importability.py`, and inspect wheel contents/entry points to verify nornir imports, asyncio registration, and exclusion of `tests/plugins/connections/async_echo.py`; record evidence in `specs/001-asyncio-runner/validation.md` and preserve dependency choices in `uv.lock`.
- [X] T059 Run the authoritative `make tests` from `Makefile` after all implementation/documentation changes, with all five gates passing; review the diff to confirm no legacy public signature/type changed and only T017 modified pre-existing tests; record actual outcomes in `specs/001-asyncio-runner/validation.md`.
- [x] T060 Verify the project's CI results for the full supported Python 3.10–3.14 and Linux/macOS/Windows matrix, including capability discovery, AsyncEcho, performance, and cancellation paths defined in `specs/001-asyncio-runner/quickstart.md`; record check URLs/platform results in `specs/001-asyncio-runner/validation.md`, keeping this gate pending if remote matrix evidence is unavailable rather than extrapolating from local results.
- [ ] T061 Walk through `specs/001-asyncio-runner/quickstart.md` and the coverage table below; record completion/blockers in `specs/001-asyncio-runner/validation.md`, confirm the follow-up issue and in-tree AsyncioRunner approval are ready to cite in the eventual PR, and re-run speckit-analyze if implementation required changes to the spec/plan/contracts.

## Dependencies and execution order

### Phase graph

```text
Setup T001–T004
  → Foundation T005–T011
      → US1 T012–T024
          → US2 T025–T040
              → US3 T041–T045
              → US4 T046–T050
                  → Final documentation/gates T051–T061
```

Both US3 and US4 are required before final gates. They can be developed in parallel only
with exclusive file ownership; their gate runs serialize once both streams are stable.
US2 registry-only code can be explored after Foundation, but its integration checkpoint
requires completed US1. No test at a phase checkpoint may call an API scheduled later.

### Within phases

- Foundation: T005, T007, T010, and the T006 → T008 → T009 stream are independent;
  T011 follows all of them. Each waits for T004.
- US1 tests: T012 → T013; T014 → T015; T016; T017. Write these streams before their
  implementation. Implementation streams: T018 → T019, T020 → T021, T022 → T023;
  all join at T024. T023 verifies the configuration/with_runner tests authored in T014.
- US2 tests: T025 → T027, T026 → T028, T029. Fixtures are local per test stream so no
  unfinished cross-file fixture dependency is introduced. Implementation: T030 → T031,
  then T032 in parallel with T033 → T034 → T035 → T036 → T037 → T038. T039 can run
  beside these once T030 defines its imported contract. T040 follows all US2 tasks.
- US3: T041 → T042 → T043 → T044 → T045.
- US4: T046, T047, T048 are separate-file test streams; T049 follows all, then T050.
- Final: T051 → T052; T053, T054, T055, and T056 can run independently after story
  checkpoints. T057/T058 follow source/docs readiness; serialize environment-mutating
  verification. T059 follows T057/T058 and all changes, T060 requires matrix evidence,
  and T061 follows both. New fixes invalidate affected gate evidence and require reruns.

### Parallel examples by story

| Story | Independent streams | Join point |
|---|---|---|
| US1 | Runner tests T012→T013; Nornir tests T014→T015; Task tests T016; registry assertion T017 | Before implementation streams and T024 |
| US2 | Registry tests T025→T027; Host tests T026→T028; echo integration tests T029 | Before implementation and T040 |
| US3 | No independent same-phase tasks: one test file and one implementation file, ordered deliberately | T045 |
| US4 | Runner tests T046; Host cancellation tests T047; echo cancellation tests T048 | T049, then T050 |

## Requirement coverage

| Requirement | Task IDs | Acceptance focus |
|---|---|---|
| FR-001 | T012, T017, T022–T024, T051 | Configuration, default, with_runner |
| FR-002 | T010, T014, T021 | Arguments/results and selection flags |
| FR-003 | T010, T014, T021 | raise_on_error and failed hosts |
| FR-004 | T012, T022 | Bounded active hosts |
| FR-005 | T005–T006, T015–T016, T019–T021, T056 | Named async-entry rejection and issue URL |
| FR-006 | T015, T020 | Coroutine-task rejection on serial/threaded |
| FR-007 | T022, T041, T043–T044 | Synchronous run/cleanup/context mismatch |
| FR-008 | T008–T009, T016, T018–T019 | Child result/failure semantics |
| FR-009 | T016, T019, T052 | Inline sync child and limitation |
| FR-010 | T016, T019 | Async child on sync entry rejection |
| FR-011 | T025–T027, T030, T035 | Base/facet contracts and legacy typing |
| FR-012 | T026, T028, T033–T036 | One logical connection and stable public cache types |
| FR-013 | T026–T028, T033, T035–T037 | Capability checks including cached transport |
| FR-014 | T026, T028, T037–T038, T041 | Both-store cleanup |
| FR-015 | T041–T045 | Observable Nornir cleanup and selection |
| FR-016 | T012, T022, T046–T050 | Single-owner cancellation and draining |
| FR-017 | T014, T016, T021, T041 | Partial event ordering and arguments |
| FR-018 | T029, T039–T040, T048, T058, T060 | Portable test-only real transport |
| FR-019 | T051–T054, T057 | Executed notebook and capability-author guide |
| FR-020 | T004, T007–T011, T017, T025, T030–T031, T059 | Public compatibility and existing-suite exception |
| FR-021 | T025, T030–T032 | New registry, all modes, both discovery groups |
| FR-022 | T025, T027, T030, T033 | Authoritative valid capability reporting |
| FR-023 | T027–T028, T033, T036 | Duplicate-name rejection, including cached lookup |
| SC-001 | T011, T017, T059–T060 | Existing-suite compatibility |
| SC-002 | T013, T022, T060 | At most 50 ms heartbeat gap |
| SC-003 | T013, T022, T060 | Under two seconds, unchanged live threads |
| SC-004 | T015–T016, T026–T028, T033, T036, T041 | Operation-specific mismatch boundaries |
| SC-005 | T025–T026, T030–T039, T053 | One registration for every declared mode |
| SC-006 | T052, T057, T059–T060 | Genuine notebook output and nbval |
| SC-007 | T025, T027, T031–T033 | Registry coexistence, discovery and invalid declarations |

## Previous task ID mapping

Only T001–T003 were completed in the prior list; they retain their IDs and completion
state. All other tasks remain pending. New T004 refreshes baseline evidence. References
to older pending IDs must use this mapping rather than their former meaning.

| Previous IDs | Revised IDs | Change |
|---|---|---|
| T001–T003 | T001–T003 | Completion preserved |
| T004–T023 | T005–T024 respectively | Expanded contracts/validation; fixed selection inputs and cancellation ownership |
| T024 | T025–T028 | Split registry/typing, lifecycle, invalid declaration, and state coverage |
| T025 | T039 | Capability-aware AsyncEcho fixture |
| T026 | T029 | Echo integration uses Host cleanup at this phase |
| T027 | T030–T032 | Base/facets, separate isolated registry, initialization discovery |
| T028 | T033–T034 | Typed validation, resolution, storage and provenance |
| T029 | T035 | Both opening paths, typed caches |
| T030 | T036 | Both retrieval paths and current ambiguity |
| T031–T032 | T037–T038, plus T035–T036 | Cleanup policy and sync access guards |
| T033 | T040 | Expanded capability/Host integration gate |
| T034 | T041–T042 | Nornir cleanup and retry tests |
| T035–T037 | T043–T045 respectively | Cleanup/context implementation and gate |
| T038 | T046–T048 | Cancellation across runner, Host, and real transport |
| T039 | T022, T049 | Cancellation ownership implemented early, audited after expanded tests |
| T040 | T050 | Cancellation gate |
| T041–T046 | T051–T056 respectively | Updated capability documentation and release prerequisites |
| T047 | T057–T060 | Docs, packaging, local five gates and matrix evidence |
| T048 | T061 | Final quickstart/coverage review |

## Implementation strategy

**MVP validation scope:** Setup + Foundation + US1, ending at T024. This demonstrates
async task execution without transport dependencies. It is not the release boundary.

Then complete US2's registry and Host lifecycle before composing Nornir cleanup in US3.
US4 validates demanding cancellation cases against the ownership already built into US1
and resource contracts from US2. Finish documentation, packaging, and all five gates plus
matrix evidence. All four stories ship together as required by the specification.

Use speckit-analyze before implementation to check this regenerated list against the
current spec and plan. Mark task completion only after its acceptance work and required
verification are actually done; unavailable CI evidence remains pending.
