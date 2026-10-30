# Data Model: Asyncio Runner and capability-aware connections

**Feature**: 001-asyncio-runner | **Updated**: 2026-10-28 | [Plan](plan.md)

## Registries and protocols

| Entity | Type / contents | Identity and validation |
|---|---|---|
| Legacy registry | Existing PluginRegister[type[ConnectionPlugin]] | Existing group and public signatures; registrations imply sync only |
| Capability registry | PluginRegister[type[CapabilityConnectionPlugin]] | Instance-owned available map; group nornir.plugins.capability_connections |
| CapabilityConnectionPlugin | get_capabilities and established connection | Structural, no-argument construction, stable instance declaration |
| ConnectionCapability | Literal["sync", "asyncio"] | Nonempty frozenset; exactly three valid combinations |
| SyncCapabilityConnectionPlugin | Base capability protocol + existing ConnectionPlugin | Both synchronous open and close |
| AsyncCapabilityConnectionPlugin | Base + aopen/aclose | Both native async methods |
| DualCapabilityConnectionPlugin | Both operation facets | Opens in either mode; the connection is bound to that mode until closed |

The capability result is authoritative but does not narrow a static type. Private guards
validate all declared operations and narrow to the appropriate facet. A declaration with
missing operations is invalid even when the current request uses another declared mode.
The connection property is accessed after opening, never used as a pre-open probe.

Cross-registry duplicate names are ambiguous, including duplicates referring to the same
class. Current ambiguity is checked on every get/open; cleanup uses cached ownership.
Replacing a registration does not replace or reclassify an already cached instance.

## Host connection state

| Field | Type | Visibility | Purpose |
|---|---|---|---|
| connections | dict[str, ConnectionPlugin] | Existing public | Legacy, capability-sync, and capability-dual instances |
| _async_connections | dict[str, AsyncCapabilityConnectionPlugin] | New private slot | Capability-asyncio-only instances |
| _capability_connections | dict[str, _CapabilityConnectionState] | New private slot | Validated origin/declaration associated with each new-contract instance |
| _opening | dict[str, asyncio.Future[None]] | New private slot | Names reserved by in-progress async opens; asynchronous getters await the future; empty when nothing is opening |

`_CapabilityConnectionState` is an immutable private record with
`plugin: CapabilityConnectionPlugin`,
`capabilities: frozenset[ConnectionCapability]` and `mode: ConnectionCapability`, the
mode that opened the connection. It references the actual plugin rather than wrapping
its operations. Legacy connections have no such record and are implicitly bound to
sync mode. Identity comparison
against the active cached object prevents stale metadata from applying after public-cache
replacement. Untracked public entries are legacy sync-only. A simultaneous public/private
entry caused by external mutation is a contract error.

### Invariants

- A managed name is in at most one instance cache and is not also opening.
- Dual-capability plugins use connections even when aopen established them.
- Every open connection has exactly one bound mode. `Host.connection_mode(name)` reports
  it and returns None for a name that is not open.
- A get in the other mode, or a synchronous close of an asyncio-bound connection, raises
  ConnectionModeMismatchError and leaves the entry intact. An asynchronous close of a
  sync-bound connection calls close inline, blocking the loop while it runs. Closing
  releases the binding.
- An asynchronous get of an opening name waits for the open, shielded so that cancelling
  one waiter does not cancel the others, and shares its outcome;
  an explicit open or a synchronous get of an opening name raises ConnectionAlreadyOpen.
- Both opening paths check all stores; only successful opening publishes state.
- Cached capability checks precede returning the transport and preserve entries on mismatch.
- Deregistering or replacing the plugin class does not change the cached object's origin.
- Successful close removes instance and matching metadata; async close failure/cancellation
  retains both for retry. Sync close preserves legacy pop-before-close behavior.
  Matching metadata is removed with the sync instance even if close raises.
- Async bulk close snapshots both stores; attempts all entries on ordinary errors and raises
  the first error afterward. Both bulk closes log each error after the first. Cancellation interrupts cleanup and propagates.
- Sync bulk cleanup snapshots both stores, attempts every name, and raises the first
  error afterwards, including the mismatch for asyncio-bound or async-only entries,
  which stay intact. Callers serialize use/cleanup while a name is closing;
  awaited-close removal checks identity so a replacement cannot be deleted accidentally.
- Filtered inventories and Nornir wrappers retaining a Host share all its connection state.
- Inventory dict/schema output omits all runtime connection state. Empty Host copy/pickle
  includes empty private slots; live transport serialization is not newly guaranteed.

### Connection state transitions

```text
absent -- validate name, declaration, mode --> reserve -- await aopen --> open
                                                  | failure/cancel       |
                                                  +--> absent            |
open -- get in the bound mode -------------------------------------------> open
open -- get or synchronous close in the other mode ---------------------> open + error
open -- successful close in the bound mode ----------------------------> absent
open -- asynchronous close of a sync-bound connection (calls close) ---> absent
open -- failed/cancelled async close -----------------------------------> open + error
open -- synchronous close (pop first) ----------------------------------> absent, even if close raises
reserved -- asynchronous get --------------------------------------------> waits, then open or the opener's error
reserved -- explicit open or synchronous get -----------------------------> unchanged + ConnectionAlreadyOpen
```

Sync opening has the same successful publication boundary without an await. A plugin is
responsible for releasing partially acquired resources before a failed/cancelled aopen
exits; the Host's finally releases its name reservation.

## Nornir run state

New methods: arun, aclose_connections, __aenter__, __aexit__. Existing signatures and
defaults remain. Preparation explicitly receives task/name/kwargs/on_good/on_failed.
The selected list preserves existing good-host then failed-host grouping and ordering.

```text
validate task -- [async path: validate runner] -- global start -- select hosts
  -- runner execution -- apply raise_on_error / update failed_hosts -- global completion
```

If raise_on_error is true and results fail, the exception precedes failed-host mutation
and global completion, matching existing behavior. Cancellation while awaiting the runner
skips finalization entirely. Async context exit cleans good and failed hosts.

## Task state and event order

Task keeps its existing callable, host, parent_task, params, and MultiResult fields.
New astart and arun share result bookkeeping helpers with start and run, calling/awaiting
the original user callable directly. Ordinary exceptions become failed results containing
the user's traceback. A CancelledError raised by the task's own code while the asyncio
task is not being cancelled becomes a failed result too (per host on Python 3.10, see
plan execution decision 6); a genuine cancellation and any other BaseException
propagate without a result.

Reject incompatible children before creating child execution events or results. The parent
already has start events; if it does not catch the mismatch, it records its normal failure.
Per-host start precedes completion; child events are nested; global completion follows
host completion when emitted. Events from different hosts may interleave.

## AsyncioRunner

Field `num_workers: int`, default 20, validated positive and non-boolean at construction.
No loop-bound state survives a call. Semaphore limits active host copies; ordered gather
preserves selected-host result order. Host futures are gathered with exceptions
returned; the runner waits for every host, then raises the first host error in host
order, as ThreadedRunner does. Only a caller cancellation makes the runner cancel its
owned futures, including waiters: wait for the aggregate without propagating the
cancellation, cancel unfinished children once, drain them under shielding, retrieve the
aggregate exception, then re-raise. Additional caller cancellations do not repeatedly
cancel children performing cleanup. It creates no executor threads.

## AsyncEcho fixture

AsyncEcho structurally implements AsyncCapabilityConnectionPlugin, reports
frozenset({"asyncio"}), and registers in the capability registry. Its connection contains
an asyncio StreamReader/StreamWriter and an async send(payload: bytes) -> bytes operation.
Opening uses a local TCP server; closing is idempotent. Fixture and server clean up partial
opens, handlers, and sockets on errors/cancellation. Nothing under tests ships in the wheel.

## Errors

See [errors.md](contracts/errors.md) for the seven mismatch errors, registry ambiguity and
contract errors, constructor argument errors, reused exceptions, and validation precedence.
The five connection-related errors are also ConnectionException instances.
