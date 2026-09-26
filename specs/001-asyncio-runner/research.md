# Research: Asyncio Runner and capability-aware connections

**Feature**: 001-asyncio-runner | **Updated**: 2026-09-13 | [Plan](plan.md)

Research includes the current core registry, Host lifecycle, Nornir initialization,
configuration, tests, and strict typing settings. The capability-aware design supersedes
the earlier async-only protocol and legacy-registry registration design.

## R1. Runner and registration

- **Decision:** AsyncioRunner stays in `nornir/plugins/runners/__init__.py`, registered as
  `asyncio` in the existing runner entry-point group, with num_workers default 20.
  It implements the existing sync runner interface by raising RunnerNotSyncError from
  run, and the new AsyncRunnerPlugin interface through arun.
- **Rationale:** Constructor, with_runner, runner property, and existing registry types
  remain unchanged. The new class structurally satisfies RunnerPlugin.
- **Alternatives:** An async-only runner object would require changing those public
  types. A new runner marker on RunnerPlugin changes the existing protocol.
- **Consequence:** The sole approved pre-existing test change is the exact runner-set
  assertion/import. Sync run can emit global task_started before rejecting AsyncioRunner;
  no host events occur. This satisfies the clarified SC-004.

## R2. Typed capability contract

- **Decision:** CapabilityConnectionPlugin defines synchronous
  `get_capabilities() -> frozenset[ConnectionCapability]` and the established connection
  property. ConnectionCapability is `Literal["sync", "asyncio"]`. Separate
  SyncCapabilityConnectionPlugin, AsyncCapabilityConnectionPlugin, and
  DualCapabilityConnectionPlugin protocols describe operation shapes. See
  [protocols.py](contracts/protocols.py) for exact signatures.
- **Rationale:** A synchronous-only plugin is first-class in the new registry; async-only
  authors do not implement fake synchronous methods. The sync facet extends the existing
  ConnectionPlugin and therefore satisfies its public return/cache types.
- **Alternatives:** An async-specific registry does not meet the agreed direction.
  Adapters or required unsupported-operation stubs add machinery not needed here.
  A literal value `both` duplicates the combination of the two independent capabilities.
  An enum is possible, but Literal with frozenset suffices for this bounded contract.
- **Decision:** Reporting is an instance method, stable for that instance, available
  before opening, with no device I/O. Classes are constructed without arguments and
  construction does no device I/O. A classmethod is unnecessary: connections already
  instantiate before opening, and instance reporting allows per-instance state without
  requiring a second metadata API.

## R3. Boundary validation and narrowing

- **Decision:** Validate a nonempty frozenset containing only the two supported strings;
  validate every declared operation pair before checking requested capability. Sync
  operations must be synchronous callables; async operations must be native async def
  methods. Do not inspect the established connection property before open. Store the
  validated declaration with the instance.
- **Rationale:** Declaration is authoritative; incidental methods do not enable modes.
  A dual declaration missing aclose must fail even on a sync request. Entry-point loading
  crosses an untyped boundary, so annotations alone cannot enforce external plugins.
- **Alternatives:** Method-presence-only detection contradicts FR-022. Runtime-checking
  a protocol with connection can evaluate a property before it is initialized. Trying
  to infer capabilities from an opening operation already performs I/O too early.
- **Typing decision:** Private TypeGuard helpers validate complete sync, async, and dual
  operation shapes. Capability membership alone cannot narrow the base type. Two
  successive TypeGuards do not reliably create an intersection; the explicit dual
  facet handles this case. Runtime shape checks cannot prove parameter signatures or
  nonblocking behavior; public facet examples and mypy cover signature conformance.
- **Author limitation:** Coroutine-function validation excludes sync wrappers returning
  awaitables. This is intentional for the new contract and must be documented.

## R4. Registry isolation and discovery

- **Decision:** New `CapabilityConnectionPluginRegister` is
  `PluginRegister[type[CapabilityConnectionPlugin]]`, with discovery group
  `nornir.plugins.capability_connections`. Explicitly assign a fresh available dictionary
  to this instance at definition time. InitNornir discovers it beside the legacy registry.
- **Rationale:** `PluginRegister.available` is currently class-level; its constructor does
  not allocate instance storage. A new registry without initialization can share entries
  with other registries. Isolating this instance prevents that without changing existing
  generic-registry behavior. The discovery name is independent of execution mode.
- **Alternatives:** Reusing the legacy group cannot unambiguously identify the registration
  contract. Globally refactoring PluginRegister storage broadens the change unnecessarily.
- **Validation:** Test cold-start registry isolation, programmatic registration, discovery
  for each capability combination, and InitNornir integration. New test fixtures snapshot
  and restore both registries, leaving pre-existing tests unchanged.

## R5. Names, cache provenance, and registry mutation

- **Decision:** Before every get/open, check whether both registries currently contain the
  name; if so reject it, including same-class duplicates and cache hits. For uncached
  names, select the single owner or raise PluginNotRegistered. For cached names retain
  the original instance and its registration mode until close. Cleanup uses cached
  ownership without consulting current registration.
- **Rationale:** FR-023 requires lookup-time ambiguity detection independent of mode or
  discovery order. Legacy cached connections remain usable after deregistration, as
  before. Closing must remain possible after registry changes.
- **Alternatives:** Preferring a registry based on requested mode violates FR-023.
  Reclassifying cached objects after registry replacement can enable unsupported calls.

## R6. Typed Host storage

- **Decision:** Preserve `Host.connections: dict[str, ConnectionPlugin]`. Store legacy,
  capability-sync, and capability-dual instances there. Store capability-asyncio-only
  instances in `_async_connections: dict[str, AsyncCapabilityConnectionPlugin]`.
  Track new-contract ownership in `_capability_connections: dict[str, _CapabilityConnectionState]`;
  each record has the original CapabilityConnectionPlugin reference and validated
  capability frozenset. `_opening: set[str]` spans both stores.
- **Rationale:** Sync and dual facets structurally satisfy the old cache and synchronous
  open return type. No false cast, widened public type, or adapter is needed. A dual
  instance opened asynchronously still goes in the public sync-compatible store.
- **Alternatives:** One public union-typed cache changes the downstream type contract.
  Putting every new-contract plugin in a private cache would hide sync-capable connections
  from existing callers unnecessarily.
- **Public mutation:** Metadata must match the actual cached object by identity. A replaced
  public-cache object is treated as legacy rather than inheriting stale metadata. External
  insertion conflicting with a private async entry is an explicit contract error.
- **Copy/serialization:** Private state is Host-owned and shared by filtered views. Use
  dictionaries, immutable records, and a set, not persistent loop-bound tasks/locks.
  Preserve inventory dict/schema output. Add empty-host copy/pickle tests: the existing
  `test_pickle.py` checks MultiResult, not Host serialization. Live transport serialization
  is not newly guaranteed.

## R7. Opening, concurrent requests, and cleanup

- **Decision:** Resolve parameters through existing Host helpers. Reserve a name before
  the first await; reject another get/open of that name; publish caches and metadata only
  on success; remove the reservation in finally. Async plugins release partial resources
  on failed/cancelled aopen. Dual plugins must reuse/close one transport across both modes.
- **Rationale:** FR-012 requires logical identity; FR-013 requires cached-mode validation.
  A lock would wait instead of producing the specified concurrent-open error.
- **Cleanup decision:** Sync close keeps pop-before-close and fail-fast bulk semantics,
  with mode rejection before removal and matching metadata removed with the instance.
  Sync bulk cleanup snapshots both stores and rejects async-only entries. Async close removes an entry only on successful
  close, retaining failures for retry. Async bulk cleanup visits a snapshot of both caches,
  attempts remaining entries after ordinary errors, and then raises the first error;
  cancellation propagates immediately. Prefer aclose for dual plugins, close for sync-only.
- **Alternatives:** Resolving registration at cleanup can strand connections after
  deregistration. Visiting only the private async cache misses dual-mode connections.
  Popping before async close prevents retry after failed/cancelled cleanup.
- **Overlap boundary:** Callers serialize access while a name is closing. General concurrent
  use/cleanup is not supported; the specified concurrent-open rejection still applies.
  After awaited close, identity-check removal to avoid deleting an externally replaced
  instance. Nornir retries after a failed cleanup include on_failed=True because failed
  hosts are skipped by default.

## R8. Shared execution semantics

- **Decision:** Share private Task helpers for beginning, result/exception conversion,
  finishing, child construction, and child recording. Keep direct calls/awaits to user
  functions visible in start/astart. The shared Nornir preparation helper receives
  `(task, name, kwargs, on_good, on_failed)` explicitly; finalization preserves current
  raise_on_error and failed_hosts order.
- **Rationale:** Sync/async parity is easier to verify when bookkeeping is shared without
  an interpreter layer. Selection flags are local inputs and cannot be inferred inside
  a helper that only receives task kwargs.
- **Alternatives:** Duplicated bodies drift; callable wrappers obscure debugger stepping.
- **Detection:** Task-kind checks use inspect.iscoroutinefunction plus the async __call__
  case for callable objects, including partials as supported on the minimum Python.
  Mismatches occur at top-level or child boundaries, not inside child execution.
- **Naming:** Keep existing Task naming: partials/callable objects without __name__ require
  explicit name. Test these forms with a name. Mismatch diagnostics safely fall back to
  the callable type's name rather than raising AttributeError.

## R9. Concurrency and cancellation

- **Decision:** AsyncioRunner creates a semaphore per invocation; schedules host copies;
  shields its ordered aggregate wait; builds results in selected-host order. On
  BaseException, explicitly cancel each unfinished owned future once, drain all children,
  and retrieve the aggregate's exception before re-raising. Shield the drain against
  subsequent caller cancellations and re-await it without re-cancelling children. Never schedule
  an executor. Validate num_workers as a positive, non-boolean integer at construction.
- **Rationale:** These APIs exist on Python 3.10. Task failures become results; unhandled
  runner/processor failures and cancellation must not leave sibling work behind.
  A zero semaphore count would hang a nonempty run.
- **Alternatives:** TaskGroup requires a newer Python; a queue/worker pool adds complexity
  without changing required behavior. No implicit sync task offload in this feature.
- **Cancellation evidence:** A read-only probe of unshielded gather followed by explicit
  child cancellation interrupted a host's awaited finally cleanup after one caller cancel:
  gather already cancelled the children, and the second cancellation interrupted cleanup.
  The runner therefore owns cancellation explicitly instead of combining both mechanisms.
- **Boundary:** Cancellation returns no aggregate and does not update failed_hosts or
  emit global completion. Previously observed processor events are not rolled back.

## R10. Errors

- **Decision:** Keep the six execution-mode errors under SyncAsyncMismatchError; add
  ConnectionPluginAmbiguousError and ConnectionPluginContractError independently.
  Constructor arguments, precedence, and message pointers are in [errors.md](contracts/errors.md).
- **Rationale:** Retrying another mode can fix a mismatch, but not duplicate registry
  names or a malformed declaration. Do not mislabel these as sync/async errors.
- **Merge precondition:** The follow-up for synchronous tasks in async runs must exist;
  replace the temporary #1085 URL in one SYNC_TASKS_IN_ASYNC_RUNS_ISSUE constant.

## R11. Processor events and performance

- **Decision:** Tests assert global boundaries, per-host start-before-completion, nested
  child ordering, and matching arguments. Permit arbitrary cross-host interleaving.
  Assert no child events/results for rejected subtasks. Preserve raise_on_error and
  cancellation omissions rather than requiring unconditional event pairing.
- **Rationale:** Comparing a concurrent event list directly to a serial list is invalid.
- **Performance decision:** Retain SC-002's 50 ms and SC-003's two-second bounds. Build
  inventories before timing; use 100 ms simulated I/O, a 10 ms heartbeat with monotonic
  timestamps, and a heartbeat-ready barrier before starting the measured run. Measure
  only the active run, recording the final heartbeat interval at run completion. SC-003
  measures awaited run time with 1,000 workers and compares live thread counts.
- **Failure policy:** Investigate CI load, measurement, and implementation. Do not loosen
  thresholds or skip failing tests to claim compliance. A changed threshold requires a
  separately approved specification change.

## R12. Test strategy and ordering

- **Decision:** Ordinary pytest functions drive asyncio.run; no new dependency. Standard
  library AsyncEcho declares asyncio only and registers in the new registry. Its local
  TCP echo server uses an ephemeral 127.0.0.1 port, portable to Windows as well as POSIX.
  Add fully typed sync-only and dual fixtures plus invalid-contract cases.
- **Ordering:** Runner/base execution first, Host/registry lifecycle next, Nornir cleanup
  next, cancellation validation and docs afterward. Host integration tests use Host
  cleanup until the Nornir cleanup API exists. Cancellation handling is part of runner
  implementation even if its exhaustive tests are grouped later.
- **Parallelism:** One owner per test file: runner behavior then runner performance;
  Nornir semantics then Nornir errors; these file streams can run independently.
- **Required coverage:** Typed examples against all facets, legacy compatibility, registry
  isolation/discovery, invalid capability declarations/operations, duplicate names before
  and after caching, both reuse directions, metadata identity, filtered Host sharing,
  four host-selection combinations, both cache cleanup, resource cancellation, traceback
  user-code visibility, and the full Python/platform matrix.

## R13. Documentation and packaging

- **Decision:** One executed how-to notebook and one plugin-author prose page, with
  literalinclude of the test-only AsyncEcho source. Include the new registry/group,
  all capability combinations, legacy coexistence, public cache visibility, stable
  capability reporting, async operation rules, and both inline blocking limitations.
  The include path from `docs/howto/` is `../../tests/plugins/connections/async_echo.py`.
- **Validation:** Notebook cells print caught named errors as genuine stored output;
  no hand-edited outputs or timing printouts. Run make nbval and make docs. The runner
  module and connection module already have generated API pages; always inspect actual
  regeneration rather than asserting generated files cannot change.
- **Packaging:** Only nornir ships; AsyncEcho stays under tests. Add the asyncio runner
  entry point and refresh installation metadata. If lock metadata needs refresh, use uv
  and retain existing dependency choices, then verify uv sync --locked.
- **Changelog:** Record #1085, capability-aware connections, and the corrected rejection
  of coroutine tasks on synchronous task entry points in the unreleased minor release.

## R14. Research evidence and limits

- Source inspection confirmed the legacy registry/cache types, shared initial registry
  dictionary, InitNornir discovery hook, filtered Host identity, and close semantics.
- Read-only mypy experiments under the repository's strict Python 3.10 settings passed
  for facet inheritance, async-only registration without sync stubs, narrowed typed-cache
  insertion, and sync-facet return as ConnectionPlugin. Negative probes confirmed that
  capability membership alone does not narrow and two TypeGuards do not preserve a dual
  intersection. Base registration alone cannot check operation/declaration consistency.
- A read-only runtime probe confirmed that explicit instance available allocation isolates
  the new registry. These are design-feasibility checks, not the full runtime feature gate.
- The revised contracts/protocols.py passes repository-configured mypy. A second inline
  probe imported these exact contracts and passed async-only base registration/private
  cache assignment plus sync/dual assignment to the unchanged legacy cache/return types.
- Ruff lint and format checks pass for the protocol artifact. A read-only asyncio probe
  of the shielded single-owner cancellation design passed with a prompt child and a child
  awaiting finally cleanup: repeated caller cancellation preserved cleanup completion,
  and no runner-owned task remained afterward. This validates the selected mechanism
  locally; the implementation must still carry regression tests across the support matrix.
- No unresolved technical choice remains in this design. The regenerated implementation
  task list maps these decisions to story phases and validation checkpoints; cross-artifact
  analysis is the next review before execution.
