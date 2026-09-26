# Implementation Plan: Asyncio Runner

**Branch**: `dga/feat-async-spplb` | **Date**: 2026-09-13 | **Spec**: [spec.md](spec.md)

**Feature directory**: `specs/001-asyncio-runner`

## Summary

Add the opt-in AsyncioRunner, Nornir.arun and async cleanup/context management, Task's
async execution methods, and capability-aware connection plugins. The connection design
uses CapabilityConnectionPlugin and CapabilityConnectionPluginRegister for sync, asyncio,
or dual-capability plugins; the existing connection protocol and registry remain the
legacy compatibility path.

The capability method is `get_capabilities() -> frozenset[ConnectionCapability]`, where
ConnectionCapability is `Literal["sync", "asyncio"]`. Separate sync, async, and dual
operation protocols permit structural typing without unsupported method stubs. New
plugins register once, manually or through `nornir.plugins.capability_connections`.

Preserve Host.connections and Host.open_connection's public types. Sync-capable plugins
use the existing cache; async-only plugins use a private typed cache. Private identity-
matched metadata records new-contract origin and validated capabilities. One logical
connection per host/name is reused across declared modes. No adapters or false casts
are needed, and changing registries does not reclassify an open connection.

The runner uses per-call bounded fan-out on the caller's event loop and cancels/drains
all owned futures on failure/cancellation. Shared private Task/Nornir helpers retain
existing result and failure semantics while directly invoking user code.

## Technical Context

- **Language/version:** Python 3.10–3.14. Use asyncio.Semaphore/gather, inspect,
  typing.Protocol/TypeGuard/Literal, and immutable metadata. No TaskGroup requirement.
- **Dependencies:** No new runtime or development dependency. Existing choices remain
  in pyproject.toml and uv.lock; tests drive asyncio.run from ordinary pytest functions.
- **Storage:** Per-Host runtime caches, not persistence. Public synchronous-compatible
  cache plus private async-only cache, capability metadata, and pending-name set.
- **Project type:** Pure Python library with structurally typed plugin contracts.
- **Platforms:** Linux, macOS, Windows. Standard-library local TCP fixtures use loopback
  and ephemeral ports; no platform-specific core behavior.
- **Testing:** make pytest first during implementation, then make tests (ruff, mypy,
  nbval, pytest, docs). New typed author examples cover all operation facets.
- **Performance:** SC-002's 100-host heartbeat gap remains at most 50 ms; SC-003's
  1,000 hosts with 100 ms I/O and 1,000 workers remains under two seconds with unchanged
  live thread count. No threshold relaxation without a specification amendment.
- **Constraints:** Existing public signatures, protocol members, default values, entry
  points, and cache types remain. Runner default stays threaded; asyncio workers default
  20. Existing tests change only for the approved exact runner-registry assertion/import.
- **Scope:** Existing core/task/inventory/connection/runner modules plus InitNornir,
  exceptions and runner entry-point metadata; new tests, executed notebook, plugin-author
  guide, plugin/configuration documentation, changelog, and generated API verification.

## Constitution Check

Design checks assess feasibility, not completed implementation or CI results.

| Principle | Pre-research | Post-design |
|---|---|---|
| I. Python-first, no DSL | PASS: ordinary tasks, protocols, and registries | PASS: start/astart directly call/await user functions; no interpreter or adapter layer; traceback/debugger checks planned |
| II. Thin core | PASS: inventory, dispatch/concurrency, registry responsibilities; no dependency additions | PASS: AsyncioRunner approval recorded in spec; AsyncEcho stays test-only; new registry is mode-neutral |
| III. Typed and verified | OPEN: old async-only legacy-registry/cache design was unsound; research required | PASS at design level: separate registry and typed caches, explicit operation facets; contract and representative author/storage mypy checks pass without casts/ignores |
| IV. Full support matrix | PASS: standard-library portable primitives | PASS at design level: portable fixture and cancellation tests planned; matrix runtime evidence remains an implementation gate |
| V. Executable/current docs | PASS: notebook, prose, changelog and generated-reference verification in scope | PASS at design level: validation guide specifies genuine notebook outputs, new registration docs and five gates |
| VI. Stable public API | OPEN: must preserve registry/cache and synchronous return types | PASS at design level: additive protocol/facets/registry; sync facet satisfies existing ConnectionPlugin; no legacy public signature changes or deprecation |

**Pre-research disposition:** Do not carry forward the previous unconditional PASS for
typing. Research R2–R6 and the type probes resolve the two open design checks before
Phase 1. No constitution violation is accepted or waived.

**Post-design result:** PASS for proceeding to task generation. Full make tests and the
supported platform/Python matrix remain required before implementation is complete.

## Design Decisions

### Connections

1. New base protocol reports a stable, nonempty capability frozenset without device I/O.
   Full signatures are in [contracts/protocols.py](contracts/protocols.py).
2. Validate declared operation pairs using separate private TypeGuard helpers, including
   an explicit dual facet. Do not probe connection before establishment. A reporting
   value alone is not a static type guard.
3. Isolate the new registry's available dictionary; InitNornir discovers both connection
   groups. Leave the existing generic registry and legacy group behavior intact.
4. Resolve current cross-registry ambiguity before get/open, including cache hits. Cached
   origin survives deregistration/replacement. Cleanup never depends on registry lookup.
5. Preserve public connections for legacy/sync/dual objects, with a private async-only
   store. Both retrieval paths check recorded capability before returning transport.
6. Async opening reserves names before suspension; publish state only on success. Plugins
   clean partial resources on unsuccessful opening. Async close retains failed entries
   for retry; async bulk cleanup attempts all names on ordinary failures, then raises.
   Sync cleanup retains existing fail-fast, pop-before-close semantics.

### Execution

1. `_prepare_run(task, name, kwargs, on_good, on_failed)` receives all selection inputs.
   Share existing finalization order, including raise_on_error behavior.
2. Task checks precede top-level/child execution. Sync subtasks run inline inside async
   tasks; synchronous processor hooks also run inline. Document both blocking limitations.
3. Processor tests assert partial ordering, not equality with a serial event list.
4. Validate positive non-boolean worker counts on AsyncioRunner construction. Per-call
   semaphore and ordered gather create no executor and retain selected-host result order.
5. Shield the initial gather wait and let the runner explicitly cancel unfinished hosts
   once, drain them under shielding, and retrieve aggregate exceptions before re-raising.
   Repeated cancellation must not interrupt host cleanup by re-cancelling children.
   Cancellation drains every owned future, including queued hosts, and skips
   global completion and failed-host mutation. Already observed events cannot be undone.

## Project Structure

### Feature artifacts

```text
specs/001-asyncio-runner/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── protocols.py
│   ├── entry-points.md
│   └── errors.md
├── quickstart.md
├── connection-registry-decision.md
├── checklists/requirements.md
└── tasks.md                 # Regenerated story tasks, coverage, and old-ID mapping
```

### Implementation targets

```text
nornir/core/__init__.py                 # Shared preparation/finalization, async APIs
nornir/core/task.py                     # Task astart/arun and shared helpers
nornir/core/inventory.py                # Two typed caches, metadata, capability dispatch
nornir/core/exceptions.py               # Six mismatches, ambiguity and contract errors
nornir/core/plugins/connections.py      # New base/facets/type alias/isolated registry
nornir/core/plugins/runners.py          # AsyncRunnerPlugin sibling
nornir/plugins/runners/__init__.py      # AsyncioRunner
nornir/init_nornir.py                   # Discover new connection group
pyproject.toml                         # asyncio runner entry point
uv.lock                                # Refresh only if package metadata requires it

tests/core/test_async_run.py            # Selection flags, results, events, cleanup
tests/core/test_async_tasks.py          # Child semantics, mismatches, tracebacks
tests/core/test_async_connections.py    # Lifecycle, capabilities, two caches, copy/filters
tests/core/test_capability_plugins.py   # Registry isolation/discovery and typed author fixtures
tests/plugins/runners/test_asyncio.py   # Workers, performance, cancellation/drain
tests/plugins/connections/async_echo.py # Test-only capability-aware AsyncEcho
tests/plugins/connections/test_async_echo.py
tests/core/test_registered_plugins.py   # Sole pre-existing assertion/import adjustment

docs/howto/asyncio_runner.ipynb
docs/howto/asyncio_runner/config.yaml
docs/howto/asyncio_runner/inventory/{hosts,groups,defaults}.yaml
docs/howto/writing_capability_connection_plugins.rst
docs/plugins/{index,execution_model}.rst
docs/configuration/parameters.rst
CHANGELOG.rst
```

No new production module is required by this layout. Still run make docs and inspect
its generated API diff; retain legitimate regeneration output instead of hand-editing it.

## Implementation Sequencing for Task Generation

1. Retain completed scaffolding; confirm baseline. Add errors, runner contract, and shared
   execution helpers with explicit selection flags; preserve synchronous regression tests.
2. Implement async task/Nornir dispatch and the runner, including cancel-and-drain. Test
   selection/result semantics, callable detection, per-host event order, worker validation,
   cancellation and performance. Keep one sequential stream per edited test/source file.
3. Add capability protocol/facets, isolated registry/discovery, validation, and typed Host
   storage/lifecycle. Test all declarations, legacy compatibility, collisions, invalid
   plugins, both reuse directions, public cache identity handling, filtered Host sharing,
   empty-host copy/pickle, failed opening, and cleanup retry.
4. Validate AsyncEcho using Host-level cleanup. This phase must not depend on the later
   Nornir cleanup API. Add Nornir cleanup/context APIs and their integration tests next.
5. Complete executable docs, changelog and follow-up issue; run make tests and the full
   support matrix. Register capability fixtures only in tests; no transport ships in core.

`tasks.md` has been regenerated against this design with explicit registry/capability
coverage, corrected phase dependencies and file-level parallelism, and a mapping from
the previous IDs. T001–T003 retain their historical completion state; T004 refreshes
baseline evidence. Run speckit-analyze before implementation.

## Phase 0: Research

Complete: [research.md](research.md), R1–R14. Resolved method shape, operation interfaces,
typed storage, discovery group, registry isolation, collision semantics, lifecycle failure
rules, worker validation, event ordering, and performance validation policy.

## Phase 1: Design and Contracts

Complete: [data-model.md](data-model.md), [contracts/](contracts/), and
[quickstart.md](quickstart.md). Public protocol signatures type-check under project mypy
settings. A representative async-only plugin registers without sync stubs; sync/dual
facets fit the unchanged public cache/return type. Runtime implementation remains future work.

## Complexity Tracking

No constitution deviations. Two instance stores and identity-matched metadata are needed
to preserve the existing public cache type while representing async-only plugins and
stable registration provenance. The alternative public union cache breaks that type
contract; metadata is not a wrapper around user task or connection execution.

## Merge Preconditions

- Tracking issue #1085 and recorded maintainer approval for in-tree AsyncioRunner.
- Dedicated synchronous-tasks-in-async-runs follow-up issue; replace the temporary URL
  in SYNC_TASKS_IN_ASYNC_RUNS_ISSUE before merge.
- All five make tests gates and supported Python/platform coverage pass, with genuine
  notebook output and reviewed generated documentation.
