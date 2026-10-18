# Implementation Plan: Async Inventory

**Branch**: `dga/feat-async-inventory-o5wf5` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-async-inventory/spec.md`

## Summary

Add `await AInitNornir(...)`, the asynchronous counterpart of `InitNornir`, so that
applications already running an event loop can build a `Nornir` object without blocking it.
Every existing inventory plugin works unchanged: `AInitNornir` runs a synchronous `load()`
and synchronous transforms in a worker thread with `asyncio.to_thread`. Plugins with async
API clients implement the new `CapabilityInventoryPlugin` contract, which follows the
capability pattern from spec 001's connection plugins, and declare `sync`, `asyncio` or both.
Transform functions defined with `async def` are awaited per host, in order, and live in a
new `AsyncTransformFunctionRegister`. `InitNornir` keeps its behaviour for every existing
plugin and transform, and raises named errors for an asyncio-only plugin or an async
transform, before anything loads.

## Technical Context

**Language/Version**: Python 3.10–3.14

**Primary Dependencies**: standard library only (`asyncio`, `inspect`, `importlib.metadata`);
`ruamel.yaml` remains the only runtime dependency

**Storage**: N/A

**Testing**: pytest functions driving `asyncio.run`, as in spec 001 (no new test dependency); nbval for the how-to
notebook

**Target Platform**: Linux, macOS, Windows

**Project Type**: library

**Performance Goals**: no measurable change to `InitNornir`; `AInitNornir` adds at most one or
two worker-thread hand-offs per call (research R4)

**Constraints**: no event loop created or driven by the core; no change to legacy protocol or
registry types; strict mypy; no new runtime dependency

**Scale/Scope**: one new entry point, five protocols, two registries, five error classes; two
modules changed for logic (`nornir/init_nornir.py`, `nornir/core/plugins/inventory.py`),
plus `nornir/core/exceptions.py` and `nornir/__init__.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Pre-research | Post-design |
|---|---|---|
| I. Python-first, no DSL | Pass. A Python coroutine and protocols; no configuration-driven behaviour added. | Pass. `pdb` works in `aload()`, in the worker thread and in async transforms; tracebacks are not wrapped (R4, FR-018). |
| II. Thin core | Pass. Inventory modelling is core scope. No new in-tree plugin; `SimpleInventory` stays sync. | Pass. Standard library only; no plugin-specific code. |
| III. Typed | Pass, to be verified by `make mypy`. | Pass. Protocols fully typed (`contracts/protocols.py`); no new ignore entries planned. |
| IV. Tested across the matrix | Pass. All behaviour is platform-neutral. | Pass. Thread and cancellation tests run on all three OSes and all five Python versions (R10). |
| V. Executable docs | Pass. Notebook, author guide and changelog planned. | Pass. `docs/howto/async_inventory.ipynb` executed by nbval; guide in `docs/howto/` (R9). |
| VI. Stable public API | Pass. Additive; ships in a MINOR release. FR-013 is a behaviour change accepted as a bug fix (spec Clarifications 2026-10-16). | Pass. Legacy protocols and registries keep their exact types. Deviation to state in the PR: FR-013 changes `InitNornir` behaviour without a deprecation period. |

**Workflow gates**: tracking issue #1087 exists; it needs a comment recording the three
decisions that differ from the proposal. No dependency change, so no dependency approval.

## Project Structure

### Documentation (this feature)

```text
specs/002-async-inventory/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── protocols.py
│   ├── errors.md
│   └── entry-points.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
nornir/
├── __init__.py                  # export AInitNornir
├── init_nornir.py               # AInitNornir, aload_inventory, shared _prepare and resolution helpers
└── core/
    ├── exceptions.py            # five new error classes (contracts/errors.md)
    └── plugins/
        └── inventory.py         # InventoryCapability, capability inventory protocols,
                                 # AsyncTransformFunction, two registers, validation helper

tests/core/
├── test_InitNornir.py           # FR-006 regression for the sync entry point (unchanged tests)
├── conftest.py                 # isolated_inventory_registries fixture (not autouse)
├── inventory_plugins.py         # shared test plugins and transforms
├── test_inventory_errors.py     # the five new error classes
├── test_capability_inventory_contract.py  # capability declaration validation, registers
├── test_async_inventory.py      # US1: AInitNornir with legacy plugins, loop, cancellation
├── test_capability_inventory.py # US2: capability contract, both entry points, errors
└── test_async_transforms.py     # US3: async and sync transforms under both entry points

docs/
├── howto/async_inventory.ipynb                      # executed how-to
└── howto/writing_capability_inventory_plugins.rst   # plugin author guide
CHANGELOG.rst                                         # feature entry + FR-013 fix entry
```

**Structure Decision**: No new module, so the generated `docs/api/` tree is not expected to
change (research R9). Code stays in the modules that already own each concept.

## Risks

- **Shared legacy registry dictionary** (research R6): ambiguity checks against legacy
  registers can report collisions with plugins of other kinds. Documented in the error
  message and the author guide. Recommend a separate bug issue for `PluginRegister`.
- **Dependency on spec 001**: `SyncAsyncMismatchError` and the asyncio test setup come from
  spec 001. This feature is implemented on top of it and merges after or with it.
- **Divergence from #1087**: reviewers who read only the issue will expect
  `AsyncInventoryPlugin` and `nornir.plugins.async_inventory`. The issue comment must land
  before the pull request is opened.

## Complexity Tracking

No constitution violations. One stated deviation for the pull request (Principle VI): FR-013
makes `InitNornir` raise for an `async def` transform without a deprecation period, because
the transform never ran.
