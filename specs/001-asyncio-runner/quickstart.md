# Quickstart: validating the capability-aware asyncio feature

**Feature**: 001-asyncio-runner | [Plan](plan.md) | [Contracts](contracts/entry-points.md)

These scenarios validate the feature after implementation. The regenerated tasks.md
maps this guide to story checkpoints; the commands below do not imply that the planned
runtime APIs or test files already exist.

## Environment and design check

```bash
uv sync --locked
uv run python --version
uv run mypy specs/001-asyncio-runner/contracts/protocols.py
```

Use a supported Python interpreter. The last command checks the proposed signatures;
it does not validate the implemented feature or third-party plugin behavior.

## Focused implementation loops

```bash
make pytest ARGS="tests/plugins/runners tests/core/test_async_run.py tests/core/test_async_tasks.py"
make pytest ARGS="tests/core/test_capability_plugins.py tests/core/test_async_connections.py tests/plugins/connections"
make mypy
make ruff
```

Keep runner tests in a sequential file-edit stream and Nornir tests in another. Before
Nornir.aclose_connections exists, the echo integration test must clean via Host methods;
the Nornir cleanup integration scenario is introduced afterward.

## 1. Registration and capability matrix — FR-011, FR-021–FR-023, SC-005/007

The new test suite provides four fixture kinds:

| Fixture | Registry | Declared capability | Expected usable paths |
|---|---|---|---|
| Unchanged legacy plugin | ConnectionPluginRegister | Implicit sync | Sync only |
| Capability sync fixture | CapabilityConnectionPluginRegister | frozenset({"sync"}) | Sync only |
| AsyncEcho | CapabilityConnectionPluginRegister | frozenset({"asyncio"}) | Asyncio only |
| Dual fixture | CapabilityConnectionPluginRegister | frozenset({"sync", "asyncio"}) | Both |

Run the capability registry and lifecycle tests. Verify:

- Programmatic registration accepts each new-contract fixture once. AsyncEcho implements
  no fake open/close methods. Typed examples conform to the relevant public operation facet.
- Automatic discovery loads `nornir.plugins.capability_connections` beside legacy
  `nornir.plugins.connections`, including through InitNornir. New registry storage is
  isolated even before any deregister_all call.
- Capability reporting works before opening and performs no device I/O. Empty/unknown
  declarations, invalid reporting methods, and missing declared operation pairs fail
  with ConnectionPluginContractError before opening. Undeclared extra methods do not
  enable a mode. A missing async close on a dual declaration fails even for sync requests.
- Cross-registry duplicate names fail with ConnectionPluginAmbiguousError, including
  identical classes and names duplicated after a connection was cached.
- Deregistration/replacement does not reclassify an existing cached object. Cleanup still
  closes it when registrations are missing or ambiguous.

## 2. Connection identity and cleanup — US2/US3, FR-012–FR-015

For the dual fixture, open synchronously and retrieve asynchronously, then repeat in the
reverse direction on a fresh host. Assert object identity and a single opening operation.
Repeat incompatible retrieval on cached and uncached sync-only/async-only fixtures;
assert the named mismatch and intact cache entry. No transport is returned on rejection.

Host.connections contains legacy/sync/dual instances; async-only instances are private.
Therefore an empty public connections dictionary alone is not proof of complete cleanup.
Tests must assert fixture close counters, resource closure, and both internal stores.

Also verify concurrent gets raise ConnectionAlreadyOpen, failed/cancelled opens release
reservations/resources, stale metadata is not applied after public-cache replacement,
filtered views share the Host's connections, and empty-host copy/pickle succeeds.

Open a legacy, capability-sync, capability-asyncio and dual connection on one host; async
bulk cleanup calls close for sync-only and aclose for async/dual. Failed async closing
retains that entry for retry and does not prevent ordinary-error cleanup of other names.
Sync mismatch leaves an async-only entry intact; legacy synchronous failure semantics stay.

After Nornir cleanup is implemented, verify async with closes good and failed hosts,
explicit cleanup honors all four on_good/on_failed combinations, and processors observe
the cleanup task. Cancellation during async closing leaves retryable cached state.
Retry through Nornir with on_failed=True after a cleanup failure, or use Host cleanup
directly. Serialize access while a connection name is closing; arbitrary overlapping
cleanup/use is outside this contract.

## 3. End-to-end async transport — AsyncEcho

```bash
make pytest ARGS="tests/plugins/connections/test_async_echo.py -vs"
```

Expected: a loopback echo server starts on an ephemeral port; each host obtains AsyncEcho
through the new registry, sends bytes and receives them back; repeat retrieval reuses
the connection; cleanup closes transports and server handlers. Repeated aclose is safe.
The same path runs on every supported OS, including Windows.

## 4. Task dispatch, errors, and processors — US1, SC-004

Run the async-run/task tests. Check ordinary tasks and callable async objects/partials
(supply explicit name for forms without __name__), positional
task/name/kwargs behavior, all four host-selection combinations, default and explicit
raise_on_error settings, failed-host bookkeeping, and zero-host warning/empty aggregate.

Top-level mismatches emit no host events. Child mismatches emit no child events/results;
uncaught errors become failed parent results. Task.run of a synchronous child remains
inline. User function names/source appear in failure tracebacks; a debugger breakpoint
steps directly into the original task.

Processor assertions allow cross-host interleaving. Require global start before host
events, per-host start before completion, nested child events, and global completion
after hosts when it is emitted. Preserve failure/cancellation omissions. The documentation
must explain that synchronous subtasks and processor callbacks can block the event loop.

## 5. Cancellation, worker counts, and performance — US4, SC-002/003

```bash
make pytest ARGS="tests/plugins/runners/test_asyncio.py"
```

Use barriers to wait until the intended hosts are running before cancelling; include
more hosts than workers to verify semaphore waiters are drained too. At the caller's
CancelledError, no runner-owned coroutine remains, failed_hosts is unchanged, and global
completion did not fire. Include a promptly cancelling host alongside one with awaited
finally cleanup, and assert that the latter finishes cleanup after one caller cancellation.
Also repeat caller cancellation while draining: it must not re-cancel host cleanup.

Validate worker count 20 by default, counts larger than inventory, and rejection of zero,
negative, non-integer and boolean values. On measured runs, retain the exact specification
thresholds: 100-host heartbeat gap at most 50 ms, and 1,000 hosts with 1,000 workers and
100 ms simulated I/O under two seconds with unchanged live thread count. Inventory setup
is outside timing; the heartbeat is ready before measurement. Investigate failures rather
than weakening thresholds to make the suite pass.

## 6. Documentation, packaging, and final gate

```bash
make tests
```

Expected: all five gates pass. Run the supported Python/OS CI matrix. The one permitted
pre-existing test edit is the runner-registry assertion/import. Inspect make docs output
for legitimate generated API changes; never hand-edit generated reference files.

Review the executed asyncio notebook and
`docs/howto/writing_capability_connection_plugins.rst`: the guide includes AsyncEcho's
real source, native async method rules, capability/discovery examples, the legacy path,
cache visibility, dual-mode transport semantics, and blocking limitations. Verify the
wheel contains nornir and excludes the test-only fixture.

Before merge:

- Record #1085 and the feature in CHANGELOG.rst, including synchronous coroutine-task rejection.
- Restate in-tree AsyncioRunner approval in the PR.
- Open the synchronous-task follow-up and replace its temporary URL in the error constant.
- Preserve genuine notebook output and review generated API changes.
- Confirm the task list's requirement coverage against actual implementation evidence,
  especially registry isolation and typed storage.
