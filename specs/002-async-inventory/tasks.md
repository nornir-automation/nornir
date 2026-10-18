---
description: "Implementation tasks for async inventory loading"
---

# Tasks: Async Inventory

**Input**: `specs/002-async-inventory/`
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md) (R1–R10),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md).

**Tests**: Required by the constitution (Principle IV). Write each story's tests before its
implementation and run them to see them fail for the expected reason (missing name or wrong
behaviour), not because of a typo. Tests are plain typed pytest functions that drive
`asyncio.run(...)`, as in spec 001; no new test dependency.

**Organization**: Three user stories. US1 is the MVP. US2 and US3 each depend on US1 (they
extend `aload_inventory`) but not on each other; they both edit `nornir/init_nornir.py`, so
their implementation tasks run one after the other.

## Format and conventions

- `- [ ] T### [P] [US#] Description with path`. `[P]` means a different file from every
  other open task in the same phase and no dependency on an unfinished task.
- Legacy names keep their exact signatures and types: `InitNornir`, `load_inventory`,
  `InventoryPlugin`, `InventoryPluginRegister`, `TransformFunction`,
  `TransformFunctionRegister`. Existing tests are not edited.
- Test registry isolation: every new test module that registers plugins starts with
  `pytestmark = pytest.mark.usefixtures("isolated_inventory_registries")`; the fixture lives
  in `tests/core/conftest.py` so pytest finds it without an import. It must snapshot and restore the dictionaries of all four inventory and
  transform registers. Never call `deregister_all()` on a legacy register, because that
  detaches it from the dictionary shared with the runner and connection registers (research R6).
- Every new public function and class has a docstring and full annotations; `make ruff` and
  `make mypy` stay clean without new ignore entries. `nornir/init_nornir.py` already has a
  per-file N802 ignore for `InitNornir`, which also covers `AInitNornir`.

---

## Phase 1: Setup

**Purpose**: confirm the starting point.

- [X] T001 Run `make pytest` and `make mypy` on the current branch and record the results in the pull request draft notes; investigate any failure before continuing, since it predates this feature
- [X] T002 Confirm spec 001 pieces this feature reuses exist: `SyncAsyncMismatchError` in `nornir/core/exceptions.py`, `asyncio` runner registered in `RunnersPluginRegister`, and the `isolated_connection_registries` fixture pattern in `tests/core/test_capability_plugins.py`

---

## Phase 2: Foundational (blocks all stories)

**Purpose**: errors, contracts, registries, validation and the shared test helpers. No
entry-point behaviour changes in this phase.

### Tests

- [X] T003 [P] Write `tests/core/test_inventory_errors.py`: for each of `InventoryPluginNotSyncError`, `TransformFunctionNotSyncError`, `InventoryPluginAmbiguousError`, `TransformFunctionAmbiguousError`, `InventoryPluginContractError`, check the base class (first two subclass `SyncAsyncMismatchError`, the rest `Exception` only — FR-016), the stored attributes (`plugin_name` / `transform_name`, plus `reason` for the contract error), and that the message contains the name and the fix listed in `specs/002-async-inventory/contracts/errors.md`
- [X] T004 [P] Write `tests/core/test_capability_inventory_contract.py` for `_validate_capability_inventory_plugin(name, plugin)` from `nornir/core/plugins/inventory.py`: valid `{"sync"}`, `{"asyncio"}` and dual plugins return their declaration; `InventoryPluginContractError` for a missing `get_capabilities`, an `async def get_capabilities`, one that raises (original exception chained as `__cause__`), a `set` instead of `frozenset`, `frozenset()`, an unknown value, `"sync"` without `load`, `"sync"` with `async def load`, `"asyncio"` without `aload`, `"asyncio"` with a plain `def aload`, and dual missing either method. Also check that `CapabilityInventoryPluginRegister.available` and `AsyncTransformFunctionRegister.available` are distinct objects from `InventoryPluginRegister.available` and from each other

### Implementation

- [X] T005 [P] Add the five error classes to `nornir/core/exceptions.py` per `specs/002-async-inventory/contracts/errors.md`, next to the spec 001 mismatch and connection registry errors, following their constructor and message style
- [X] T006 [P] Add to `nornir/core/plugins/inventory.py`: `CAPABILITY_INVENTORY_PLUGIN_PATH`, `ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH`, `InventoryCapability`, the protocols `CapabilityInventoryPlugin`, `SyncCapabilityInventoryPlugin`, `AsyncCapabilityInventoryPlugin`, `DualCapabilityInventoryPlugin`, `AsyncTransformFunction`, and the registers `CapabilityInventoryPluginRegister` and `AsyncTransformFunctionRegister`, each assigned its own `available = {}` dictionary; signatures exactly as in `specs/002-async-inventory/contracts/protocols.py`. Leave existing names untouched
- [X] T007 Implement `_validate_capability_inventory_plugin(name: str, plugin: CapabilityInventoryPlugin) -> frozenset[InventoryCapability]` in `nornir/core/plugins/inventory.py` with the four steps in research R2, mirroring `_validate_capability_plugin` in `nornir/core/inventory.py` but raising `InventoryPluginContractError`; add TypeGuard helpers for the sync and async sub-protocols (depends on T005, T006)
- [X] T008 Refactor `nornir/init_nornir.py` without changing behaviour: extract `_prepare(config_file, dry_run, *, inventory, ssh, logging, core, runner, user_defined) -> tuple[Config, GlobalState]` (connection auto-registration, `Config.from_file`/`from_dict`, `config.logging.configure()`), and make `InitNornir` call it (research R8). Run `make pytest` to confirm no change
- [X] T009 Create `tests/core/conftest.py` with a fixture `isolated_inventory_registries` that snapshots and restores the four registers' dictionaries (see conventions); it is not autouse, so existing tests in `tests/core/` are unaffected. Create `tests/core/inventory_plugins.py` with: a `build_test_inventory() -> Inventory` returning a small deterministic inventory of at least three hosts; recording test plugins `LegacyPlugin`, `SyncCapabilityPlugin`, `AsyncCapabilityPlugin`, `DualCapabilityPlugin` (each records which of `__init__`, `get_capabilities`, `load`, `aload` ran, and the thread id of `load`); and a `BlockingLegacyPlugin` whose `load()` waits on a `threading.Event` passed through options (depends on T006)
- [X] T010 Run T003 and T004 and confirm they pass; run `make mypy` and `make ruff`

**Checkpoint**: contracts, errors and validation exist and are tested; entry points unchanged.

---

## Phase 3: User Story 1 — Build Nornir from an async application with any existing plugin (P1) 🎯 MVP

**Goal**: `await AInitNornir(...)` works with every legacy inventory plugin, without
blocking the loop.

**Independent test**: with `SimpleInventory` and `BlockingLegacyPlugin`, the loop keeps
running during the load and the inventory equals what `InitNornir` builds.

### Tests (write first, see them fail)

- [X] T011 [US1] Write `tests/core/test_async_inventory.py` (T009 plugins; module-level `pytestmark` for the T009 fixture), one test per item:
  - parametrized over every inventory configuration used in `tests/core/test_InitNornir.py` (config file, programmatic `SimpleInventory` options, the `inventory-test` plugin, `transform_func` with and without options): `AInitNornir` returns a `Nornir` whose `inventory.dict()` equals `InitNornir`'s for the same arguments; for the bad-options transform case both raise the same exception type (acceptance 1.1, SC-002)
  - a coroutine scheduled before `await AInitNornir(...)` sets the `BlockingLegacyPlugin` event; the call completes, proving `load()` ran off the loop; wrap in `asyncio.wait_for` with a short timeout so a regression fails instead of hanging (acceptance 1.2, FR-003, SC-003)
  - `LegacyPlugin.load` thread id differs from the loop thread id (FR-003)
  - a legacy plugin whose `load()` calls `asyncio.run(some_coroutine())` succeeds under `AInitNornir` (acceptance 1.3, FR-005)
  - `inspect.signature(AInitNornir)` has the same parameters, kinds and defaults as `InitNornir`, and calling it with `dry_run=True`, `runner={"plugin": "serial"}`, `core`, `logging`, `user_defined` produces the same `config` values and `data.dry_run` as `InitNornir` (acceptance 1.4, FR-001, FR-002)
  - an empty inventory returns a `Nornir` with no hosts
  - an exception raised by `load()` propagates with its type and traceback pointing into the plugin's `load` frame (FR-018)
  - cancelling the `AInitNornir` task while `BlockingLegacyPlugin` waits raises `CancelledError` within a short timeout and no `Nornir` is returned (FR-017, SC-007). Inside the same scenario coroutine, after that assertion and before it returns, set the event; `asyncio.run()` waits for the default executor's threads when it exits, so setting the event later would hang the test
  - `from nornir import AInitNornir` works and `"AInitNornir" in nornir.__all__`
  - `AInitNornir` works with `ThreadedRunner`, `SerialRunner` and the asyncio runner (spec assumption)
- [X] T012 [US1] Run `uv run pytest tests/core/test_async_inventory.py` and confirm the tests fail because `AInitNornir` does not exist

### Implementation

- [X] T013 [US1] In `nornir/init_nornir.py`, add `async def aload_inventory(config: Config) -> Inventory` for the legacy path: auto-register `InventoryPluginRegister`, resolve the plugin, construct it with `config.inventory.options`, then run `load()` and any configured synchronous transform loop together in one `await asyncio.to_thread(...)` call (research R4). Keep the existing sync transform behaviour for now; US3 extends it
- [X] T014 [US1] In `nornir/init_nornir.py`, add `async def AInitNornir(...)` with exactly `InitNornir`'s parameters and docstring adapted, built from `_prepare` and `await aload_inventory(config)` then `load_runner(config)` (FR-001, FR-002)
- [X] T015 [US1] Export `AInitNornir` from `nornir/__init__.py` and add it to `__all__`
- [X] T016 [US1] Run `uv run pytest tests/core/test_async_inventory.py tests/core/test_InitNornir.py`, then `make mypy` and `make ruff`

**Checkpoint**: MVP. Every existing inventory plugin works from an async application.

---

## Phase 4: User Story 2 — Ship an inventory plugin that supports async loading (P2)

**Goal**: capability inventory plugins load through both entry points according to their
declaration, with named errors for unsupported combinations.

**Independent test**: a dual plugin is loaded with `aload()` by `AInitNornir` and `load()`
by `InitNornir`; an asyncio-only plugin makes `InitNornir` raise before any loading method.

### Tests (write first, see them fail)

- [X] T017 [US2] Write `tests/core/test_capability_inventory.py` (T009 plugins; module-level `pytestmark` for the T009 fixture), one test per item:
  - dual plugin: `AInitNornir` calls `aload` only, `InitNornir` calls `load` only (acceptance 2.1, 2.2, FR-004, FR-007)
  - asyncio-only plugin: `AInitNornir` awaits `aload`; `InitNornir` raises `InventoryPluginNotSyncError` whose message names `AInitNornir`, and `load`/`aload` were not called (acceptance 2.3, FR-007)
  - sync-only capability plugin: `AInitNornir` runs `load` in a thread other than the loop thread; `InitNornir` calls `load` (acceptance 2.4, FR-003)
  - `aload` that awaits `asyncio.sleep(0)` repeatedly lets another coroutine run in between (SC-003, asyncio plugin)
  - the same name registered in `InventoryPluginRegister` and `CapabilityInventoryPluginRegister` raises `InventoryPluginAmbiguousError` from both entry points before `__init__` runs (FR-014)
  - a capability plugin registered under a name already used by a legacy runner (`threaded`) raises `InventoryPluginAmbiguousError` from both entry points; the message names both registries (FR-014, spec edge case)
  - an invalid declaration raises `InventoryPluginContractError` from both entry points before `load`/`aload` runs (FR-015)
  - a name in neither register raises `PluginNotRegistered` from both entry points
  - entry-point discovery: monkeypatch `importlib.metadata.entry_points` so that only group `nornir.plugins.capability_inventory` advertises a dual plugin once; both entry points load it (SC-006)
  - cancelling `AInitNornir` during an `aload` that awaits an `asyncio.Event` delivers `CancelledError` into `aload` (checked by a `finally` flag) and to the caller
  - an exception raised in `aload` propagates with a traceback into the plugin's frame (FR-018)
- [X] T018 [US2] Run `uv run pytest tests/core/test_capability_inventory.py` and confirm failures are for missing capability handling

### Implementation

- [X] T019 [US2] In `nornir/init_nornir.py`, add `_resolve_inventory_plugin(config)` per `specs/002-async-inventory/contracts/entry-points.md`: auto-register both inventory registers, raise `InventoryPluginAmbiguousError` if the name is in both, return the legacy or capability class with a flag, raise `PluginNotRegistered` if in neither
- [X] T020 [US2] Use `_resolve_inventory_plugin` and `_validate_capability_inventory_plugin` in `load_inventory`: legacy → `load()` as today; capability with `"sync"` → `load()`; asyncio-only → `InventoryPluginNotSyncError` before any loading method (FR-006, FR-007). Keep the order of operations in `specs/002-async-inventory/data-model.md`
- [X] T021 [US2] Use the same helpers in `aload_inventory`: `"asyncio"` declared → `await plugin.aload()`, otherwise `load()` in the worker thread as in T013 (FR-003, FR-004)
- [X] T022 [US2] Run `uv run pytest tests/core/test_capability_inventory.py tests/core/test_async_inventory.py tests/core/test_InitNornir.py`, then `make mypy` and `make ruff`

**Checkpoint**: plugin authors can ship sync, asyncio or dual inventory plugins.

---

## Phase 5: User Story 3 — Enrich hosts with an async transform function (P3)

**Goal**: `async def` transforms are awaited per host, in order, by `AInitNornir`; sync
transforms run in the worker thread; `InitNornir` refuses async transforms before loading.

**Independent test**: an async transform records start/end per host; records follow
inventory order without overlap. `InitNornir` with the same transform raises before `load()`.

### Tests (write first, see them fail)

- [X] T023 [US3] Write `tests/core/test_async_transforms.py` (T009 plugins; module-level `pytestmark` for the T009 fixture), one test per item:
  - async transform registered in `AsyncTransformFunctionRegister`: `AInitNornir` produces `start`/`end` records for every host in inventory order, each `end` before the next `start`, and receives `transform_function_options` as keyword arguments (acceptance 3.1, FR-011)
  - the same with an asyncio-only plugin, so `aload` and the transforms both run on the loop
  - sync transform under `AInitNornir` runs in a thread other than the loop thread, for both a legacy plugin and an asyncio plugin (acceptance 3.2, FR-012)
  - `InitNornir` with an async transform raises `TransformFunctionNotSyncError` naming `AInitNornir`, and the plugin's `load` was not called (acceptance 3.3, FR-013)
  - an `async def` transform registered in the legacy `TransformFunctionRegister` is awaited by `AInitNornir` and refused by `InitNornir` (research R5)
  - a plain function registered in `AsyncTransformFunctionRegister` runs normally under `InitNornir` and in the thread under `AInitNornir` (research R5)
  - an async transform raising on the third host propagates, and no `Nornir` is returned (acceptance 3.4)
  - the same name in both transform registers raises `TransformFunctionAmbiguousError` from both entry points before the plugin is constructed (FR-014)
  - an unregistered transform name raises `PluginNotRegistered` from both entry points
  - error precedence per `specs/002-async-inventory/contracts/errors.md`: an ambiguous plugin name wins over an async transform under `InitNornir`
- [X] T024 [US3] Run `uv run pytest tests/core/test_async_transforms.py` and confirm failures are for missing transform handling

### Implementation

- [X] T025 [US3] In `nornir/init_nornir.py`, add `_resolve_transform(config)`: when a transform is configured, auto-register both transform registers, raise `TransformFunctionAmbiguousError` for a name in both, `PluginNotRegistered` for neither, and return the callable with `inspect.iscoroutinefunction(...)` as its kind
- [X] T026 [US3] In `load_inventory`, resolve the transform before constructing the plugin and raise `TransformFunctionNotSyncError` for a coroutine function (FR-013); keep calling sync transforms per host exactly as today
- [X] T027 [US3] In `aload_inventory`, apply the thread grouping table from research R4: sync plugin + sync transform in one thread call; sync plugin + async transform → thread for `load()` then `await` each host's transform in order; asyncio plugin + sync transform → `await aload()` then one thread call for all transforms; asyncio plugin + async transform → all on the loop (FR-011, FR-012)
- [X] T028 [US3] Run `uv run pytest tests/core/`, then `make mypy` and `make ruff`

**Checkpoint**: all three stories complete.

---

## Phase 6: Documentation and cross-cutting gates

- [X] T029 [P] Create `docs/howto/async_inventory.ipynb`: top-level `await AInitNornir(...)` with `SimpleInventory` on a small inventory stored in `docs/howto/async_inventory/` (configuration and YAML files, as `docs/howto/asyncio_runner/` does); a minimal dual capability plugin registered in-process with `CapabilityInventoryPluginRegister.register`; an async transform; a cell showing `InventoryPluginNotSyncError` from `InitNornir`. Execute it and commit the real output; add sanitisation to `docs/nbval_sanitize.cfg` only for values that vary between runs (FR-019)
- [X] T030 [P] Create `docs/howto/writing_capability_inventory_plugins.rst`, modelled on `docs/howto/writing_capability_connection_plugins.rst`: the contract and declaration rules, the no-I/O constructor rule, the `nornir.plugins.capability_inventory` and `nornir.plugins.async_transform_function` groups with `pyproject.toml` examples, why the same name must not be registered in both inventory groups (and the shared-dictionary collision note from research R6), async transform rules (`async def` only, sequential), and cancellation of synchronous plugins with the advice to set network timeouts (FR-019)
- [X] T031 [P] Add two entries under `3.7.0 - Unreleased` in `CHANGELOG.rst`: the feature (AInitNornir, capability inventory plugins, async transforms; #1087) and the fix (`InitNornir` raises `TransformFunctionNotSyncError` instead of silently skipping an `async def` transform; #1087)
- [X] T032 Run `make docs` and commit anything it regenerates under `docs/api/` (none is expected: no module was added)
- [X] T033 Run `make tests` (ruff, mypy, nbval, pytest, docs); all five must pass
- [X] T034 Walk through `specs/002-async-inventory/quickstart.md` sections 2 and 3 by hand and confirm the expected results
- [ ] T035 (drafted, waiting for approval to post) Draft a comment for #1087 recording the three decisions that differ from the proposal (capability inventory registry instead of `AsyncInventoryPluginRegister`, worker thread for synchronous plugins under `AInitNornir`, async transforms in v1 with their own registry) and the reason for each, linking `specs/002-async-inventory/research.md`; show it to the user and post it only after approval, before the pull request is opened
- [X] T036 Prepare the pull request notes: link #1087; list the three decisions that differ from the proposal (capability registry, worker thread, async transforms with their own registry); state the Principle VI deviation for FR-013 and cite the spec 001 precedent in 3.7.0 (`AsyncTaskOnSyncRunError` replaced a silent un-awaited coroutine result); confirm by hand that `pdb.set_trace()` stops inside `aload()`, inside a synchronous `load()` under `AInitNornir`, and inside an async transform (FR-018), and say so; state that tests ran on Linux locally and rely on CI for macOS and Windows; mention the shared `PluginRegister` dictionary finding and the recommended separate bug issue

---

## Dependencies and execution order

### Phase graph

```text
Phase 1 Setup ─► Phase 2 Foundational ─► Phase 3 US1 (MVP) ─┬─► Phase 4 US2 ─┐
                                                           └─► Phase 5 US3 ─┴─► Phase 6
```

US2 and US3 are independent in behaviour, but both edit `nornir/init_nornir.py`. Their test
tasks (T017, T023) can be written in parallel; their implementation tasks run one story at a
time. If US3 runs before US2, T025–T027 work on the legacy-only resolution from T013.

### Within phases

- Phase 2: T003, T004, T005, T006 in parallel → T007 (needs T005, T006) → T008 → T009 (needs T006) → T010.
- Each story: tests → see them fail → implementation in task order → run tests and gates.
- Phase 6: T029, T030, T031 in parallel → T032 → T033 → T034 → T035 → T036.

### Parallel examples

- **Phase 2**: `T003 tests/core/test_inventory_errors.py`, `T004 tests/core/test_capability_inventory_contract.py`, `T005 nornir/core/exceptions.py`, `T006 nornir/core/plugins/inventory.py`.
- **After US1**: `T017 tests/core/test_capability_inventory.py` and `T023 tests/core/test_async_transforms.py`.
- **Phase 6**: `T029` notebook, `T030` guide, `T031` changelog.

## Requirement coverage

| Requirement | Tests | Implementation |
|---|---|---|
| FR-001, FR-002 | T011 | T008, T014, T015 |
| FR-003 | T011, T017 | T013, T021 |
| FR-004 | T017 | T021 |
| FR-005 | T011 | T013 |
| FR-006 | existing `tests/core/test_InitNornir.py`, T017 | T020 |
| FR-007 | T017 | T020 |
| FR-008 | T004 | T006, T007 |
| FR-009 | T004, T017 | T006, T019 |
| FR-010 | T004, T023 | T006, T025 |
| FR-011 | T023 | T027 |
| FR-012 | T023 | T013, T027 |
| FR-013 | T023 | T026, T031 |
| FR-014 | T017 (including legacy name clash), T023 | T019, T025 |
| FR-015 | T004, T017 | T007, T020, T021 |
| FR-016 | T003 | T005 |
| FR-017 | T011, T017 | T013, T021 |
| FR-018 | T011, T017, T036 (pdb by hand) | T013, T021 |
| FR-019 | T033 (nbval, docs) | T029, T030, T031 |
| SC-001, SC-002 | T011 | T014 |
| SC-003 | T011, T017, T023 | T013, T021, T027 |
| SC-004 | T016, T022, T028, T033 | — |
| SC-005 | T017, T023 | T020, T026 |
| SC-006 | T017 | T006, T019 |
| SC-007 | T011 | T013 |

## Implementation strategy

1. **MVP (Phases 1–3)**: errors, contracts and `AInitNornir` for legacy plugins. This alone
   answers the request from the #1087 review: every existing plugin works from an async
   application without blocking the loop.
2. **US2**: capability inventory plugins; opens the path for Infrahub, NetBox and Nautobot
   plugins with async clients.
3. **US3**: async transforms and the `InitNornir` fix for silently skipped `async def`
   transforms.
4. **Phase 6**: documentation, changelog, full gates, pull request notes.

All stories ship in the same MINOR release as spec 001 or a later one; the checkpoints
validate increments and are not separate releases.
