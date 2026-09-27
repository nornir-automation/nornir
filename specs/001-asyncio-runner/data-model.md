# Data Model: Asyncio Runner and capability-aware connections

**Feature**: 001-asyncio-runner | **Updated**: 2026-09-13 | [Plan](plan.md)

## Registries and protocols

| Entity | Type / contents | Identity and validation |
|---|---|---|
| Legacy registry | Existing PluginRegister[type[ConnectionPlugin]] | Existing group and public signatures; registrations imply sync only |
| Capability registry | PluginRegister[type[CapabilityConnectionPlugin]] | Instance-owned available map; group nornir.plugins.capability_connections |
| CapabilityConnectionPlugin | get_capabilities and established connection | Structural, no-argument construction, stable instance declaration |
| ConnectionCapability | Literal["sync", "asyncio"] | Nonempty frozenset; exactly three valid combinations |
| SyncCapabilityConnectionPlugin | Base capability protocol + existing ConnectionPlugin | Both synchronous open and close |
| AsyncCapabilityConnectionPlugin | Base + aopen/aclose | Both native async methods |
| DualCapabilityConnectionPlugin | Both operation facets | Same transport reusable/closable through either mode |

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
| _opening | set[str] | New private slot | Names reserved by in-progress async opens |

`_CapabilityConnectionState` is an immutable private record with
`plugin: CapabilityConnectionPlugin` and
`capabilities: frozenset[ConnectionCapability]`. It references the actual plugin rather
than wrapping its operations. Legacy connections have no such record. Identity comparison
against the active cached object prevents stale metadata from applying after public-cache
replacement. Untracked public entries are legacy sync-only. A simultaneous public/private
entry caused by external mutation is a contract error.

### Invariants

- A managed name is in at most one instance cache and is not also opening.
- Dual-capability plugins use connections even when aopen established them.
- Both opening paths check all stores; only successful opening publishes state.
- Cached capability checks precede returning the transport and preserve entries on mismatch.
- Deregistering or replacing the plugin class does not change the cached object's origin.
- Successful close removes instance and matching metadata; async close failure/cancellation
  retains both for retry. Sync close preserves legacy pop-before-close behavior.
  Matching metadata is removed with the sync instance even if close raises.
- Async bulk close snapshots both stores; attempts all entries on ordinary errors and raises
  the first error afterward. Cancellation interrupts cleanup and propagates.
- Sync bulk cleanup snapshots both stores, remains fail-fast, and raises a mismatch for
  async-only entries. Callers serialize use/cleanup while a name is closing; awaited-close
  removal checks identity so a replacement cannot be deleted accidentally.
- Filtered inventories and Nornir wrappers retaining a Host share all its connection state.
- Inventory dict/schema output omits all runtime connection state. Empty Host copy/pickle
  includes empty private slots; live transport serialization is not newly guaranteed.

### Connection state transitions

```text
absent -- validate name, declaration, mode --> reserve -- await aopen --> open
                                                  | failure/cancel       |
                                                  +--> absent            |
open -- supported get, either declared mode ----------------------------> open
open -- incompatible get/close -----------------------------------------> open + error
open -- successful close -----------------------------------------------> absent
open -- failed/cancelled async close -----------------------------------> open + error
open -- synchronous close (pop first) ----------------------------------> absent, even if close raises
reserved -- another get/open ------------------------------------------> unchanged + ConnectionAlreadyOpen
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
the user's traceback; BaseException propagates without a cancellation result.

Reject incompatible children before creating child execution events or results. The parent
already has start events; if it does not catch the mismatch, it records its normal failure.
Per-host start precedes completion; child events are nested; global completion follows
host completion when emitted. Events from different hosts may interleave.

## AsyncioRunner

Field `num_workers: int`, default 20, validated positive and non-boolean at construction.
No loop-bound state survives a call. Semaphore limits active host copies; ordered gather
preserves selected-host result order. The runner owns and drains all scheduled host
futures, including waiters, on BaseException. Wait for the initial aggregate without
propagating caller cancellation and give the runner sole ownership of child cancellation:
cancel unfinished children once, drain
them under shielding, and retrieve the aggregate exception before re-raising. Additional
caller cancellations do not repeatedly cancel children performing cleanup. It creates
no executor threads.

## AsyncEcho fixture

AsyncEcho structurally implements AsyncCapabilityConnectionPlugin, reports
frozenset({"asyncio"}), and registers in the capability registry. Its connection contains
an asyncio StreamReader/StreamWriter and an async send(payload: bytes) -> bytes operation.
Opening uses a local TCP server; closing is idempotent. Fixture and server clean up partial
opens, handlers, and sockets on errors/cancellation. Nothing under tests ships in the wheel.

## Errors

See [errors.md](contracts/errors.md) for the six mismatch errors, registry ambiguity and
contract errors, constructor argument errors, reused exceptions, and validation precedence.
