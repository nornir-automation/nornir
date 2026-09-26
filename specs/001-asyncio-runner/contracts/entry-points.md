# Contract: execution, registration, and connection lifecycle

**Feature**: 001-asyncio-runner | [Protocols](protocols.py) | [Errors](errors.md)

## Nornir and Task

New signatures:

```python
async def Nornir.arun(
    self,
    task: Callable[..., Coroutine[Any, Any, Any]],
    raise_on_error: bool | None = None,
    on_good: bool = True,
    on_failed: bool = False,
    name: str | None = None,
    **kwargs: Any,
) -> AggregatedResult

async def Nornir.aclose_connections(
    self, on_good: bool = True, on_failed: bool = False,
) -> None

async def Nornir.__aenter__(self) -> Nornir
async def Nornir.__aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    traceback: TracebackType | None,
) -> None

async def Task.astart(self, host: Host) -> MultiResult
async def Task.arun(
    self, task: Callable[..., Coroutine[Any, Any, Any]], **kwargs: Any,
) -> MultiResult
```

Existing public signatures stay unchanged. `Nornir.arun` validates task kind and runner
support, emits global start, selects hosts using the same on_good/on_failed behavior as
`run`, awaits the runner, then applies the existing finalization rules. With
raise_on_error false, failed hosts are updated; with true, result.raise_on_error runs
first and may prevent global completion. Zero selected hosts logs the existing warning.

The shared private preparation helper receives all five inputs explicitly:
`_prepare_run(task, name, kwargs, on_good, on_failed)`. Neither selection flag is hidden
in task keyword arguments or instance state.

`Task.astart` awaits user code directly and applies the same result coercion, naming,
severity, exception conversion, and processor events as `start`. `Task.arun` constructs
and executes a child, then uses the same result insertion and NornirSubTaskError logic
as `run`. A mismatch is rejected before child execution or child events; an uncaught
mismatch in user code becomes a failed parent result, not a fabricated child result.
`Task.run(def_subtask)` remains inline even inside async code and must not block the loop.
Callable instances and partials without __name__ require an explicit name, preserving
existing Task naming behavior. Tests of these forms pass name explicitly. Mismatch
diagnostics use the explicit name, a string __name__, or the callable's type name so
validation never fails with AttributeError while constructing its error message.

`aclose_connections` dispatches an async host-cleanup task through `arun`.
Async context entry returns self; exit cleans good and failed hosts by passing both
selection flags as true. Sync context exit and sync cleanup on AsyncioRunner raise
RunnerNotSyncError with the async alternatives.

Cancellation escapes as BaseException. The runner shields its initial aggregate wait,
then explicitly cancels each unfinished owned host future once on failure/cancellation
(including semaphore waiters). It drains all children and retrieves the aggregate's
exception before re-raising. Shield draining from subsequent caller cancellations and
continue awaiting it without re-cancelling children, so awaited host cleanup can finish.
Do not both let gather propagate cancellation and then cancel its children again: that
can interrupt cleanup after a single caller cancellation. Global completion and failed-host updates do not
run. Events/results already observed by processors before cancellation cannot be rolled
back; no aggregate or cancellation result is returned.

## Capability-aware registration

Public types and the registry are defined in [protocols.py](protocols.py), intended for
`nornir.core.plugins.connections`. The primary protocol is CapabilityConnectionPlugin;
the sync, async, and dual facets describe its supported operation combinations. No
inheritance is required of plugin authors, and no unsupported operation stubs are required.

```python
def get_capabilities(self) -> frozenset[ConnectionCapability]
ConnectionCapability = Literal["sync", "asyncio"]
```

The three legal declarations are `frozenset({"sync"})`, `frozenset({"asyncio"})`, and
`frozenset({"sync", "asyncio"})`. Reporting is synchronous, does no device I/O, and is
stable during the instance's lifetime. Construction takes no arguments and does no
device I/O. Both operations in every declared mode must be present; sync methods must
be synchronous callables and async methods native coroutine functions. Full parameter
conformance can be checked through facet annotations and mypy; runtime validation checks
the documented operation shape rather than proving signatures for every external plugin.
A declaration does not narrow the protocol's static type.

Programmatic registration uses the ordinary registry API once per plugin:

```python
CapabilityConnectionPluginRegister.register("transport", PluginClass)
```

Automatic discovery uses the new, execution-neutral group:

```toml
[project.entry-points."nornir.plugins.capability_connections"]
transport = "transport_package:PluginClass"
```

InitNornir calls both connection registries' auto_register methods before inventory load.
Direct Nornir construction continues to rely on explicitly prepared registries. Existing
ConnectionPluginRegister, its type, and `nornir.plugins.connections` remain unchanged.
Legacy registrations are sync-only regardless of extra methods. Only the new registry
gets explicit instance-owned available storage at definition time.

On every get/open, including a cache hit, check current membership in both registries.
A name present in both raises ConnectionPluginAmbiguousError, even for the same class.
For an uncached name, select its sole registry or raise PluginNotRegistered. For a
cached name with no cross-registry conflict, retain the cached object's recorded origin
and declaration even if its registration was removed/replaced. Changing registration
does not migrate an open connection. Cleanup uses cached ownership, never a fresh lookup.

Malformed reporting methods, invalid declarations, and missing declared operations raise
ConnectionPluginContractError before opening. Validate all declared modes, including
the mode not requested by this call. Do not access the established connection property
during pre-open validation. Extra undeclared operations never enable a mode.

## Host entry points and storage

```python
async def Host.aget_connection(self, connection: str, configuration: Config) -> Any
async def Host.aopen_connection(
    self,
    connection: str,
    configuration: Config,
    hostname: str | None = None,
    username: str | None = None,
    password: str | None = None,
    port: int | None = None,
    platform: str | None = None,
    extras: dict[str, Any] | None = None,
    default_to_host_attributes: bool = True,
) -> AsyncCapabilityConnectionPlugin
async def Host.aclose_connection(self, connection: str) -> None
async def Host.aclose_connections(self) -> None
```

Parameter resolution mirrors the synchronous methods. `open_connection` retains its
ConnectionPlugin return annotation; a validated sync or dual facet satisfies it
structurally. Both opening methods return the plugin instance; get methods return
its established transport.

| Registered kind | Storage | Sync path | Async path | Async cleanup |
|---|---|---|---|---|
| Legacy | Existing connections | open/get/close | Mismatch | close |
| Capability sync | Existing connections + private origin metadata | open/get/close | Mismatch | close |
| Capability asyncio | Private async cache + origin metadata | Mismatch | aopen/aget/aclose | await aclose |
| Capability both | Existing connections + private origin metadata | open/get/close | aopen/aget/aclose | await aclose |

`Host.connections: dict[str, ConnectionPlugin]` remains the synchronous-compatible public
cache. It does not enumerate async-only connections. One logical connection name spans
both stores, and dual-mode instances are stored only once, regardless of opening mode.
Both retrieval methods check recorded capabilities before returning a cached transport;
mismatch leaves the entry intact. Capability metadata is associated by object identity,
so replacing a public-cache entry cannot transfer the old object's declared capabilities.
Untracked public-cache entries retain legacy sync semantics. Conflicting public/private
entries caused by external mutation raise a contract error rather than selecting one.

Open checks both stores and a private pending-name set. A repeated get/open of an opening
name raises ConnectionAlreadyOpen. The reservation is set before the first await and
cleared in finally. Publish the instance and its metadata only after opening succeeds.
Failed/cancelled aopen must release partially acquired resources inside the plugin;
the host removes its reservation and does not publish the instance.

Sync close validates support before removal, then removes the instance and matching
metadata before calling close, retaining existing pop-before-close semantics even if
close raises. Sync bulk cleanup snapshots both stores and is fail-fast; encountering
an async-only name raises the mismatch rather than silently omitting it.
Async close dispatches using recorded capabilities, removes cache/metadata
after successful closing, and retains them if closing fails or is cancelled for retry.
Async bulk cleanup snapshots both stores; ordinary close errors do not prevent attempts
on the remaining names, and the first error is raised afterward. Cancellation propagates
immediately. Existing synchronous bulk cleanup remains fail-fast. Neither cleanup path
requires the plugin still be registered. Missing names raise ConnectionNotOpen.

Only concurrent opening of the same name is supported as specified. Callers must serialize
get/open/close operations against a name while it is closing; overlapping cleanup and use
are not supported. After an awaited close, remove only the instance/metadata whose identity
matches the object closed, so an external replacement is not accidentally removed.
A failed Nornir cleanup can mark the host failed; retry through Nornir with on_failed=True
or invoke Host cleanup directly rather than relying on default good-host selection.

All managed cache mutation and private bookkeeping belong to Host; Nornir views/filters sharing a Host share its caches.
Inventory dict/schema output continues to omit connections. Empty-host copy/pickle must
work; serializing live transport objects is not newly guaranteed.

## Runner and processor event contract

AsyncioRunner implements both RunnerPlugin and AsyncRunnerPlugin. Its sync run always
raises RunnerNotSyncError; async run uses a per-call semaphore and ordered gather.
num_workers defaults to 20; construction rejects booleans/non-integers with TypeError
and nonpositive integers with ValueError. Existing runner validation is unchanged.

Global task_started precedes host events. Each host's start precedes its completion;
child events are nested within the parent. Global task_completed, when emitted, follows
all host completions. Cross-host interleaving is unrestricted. Processors run synchronously
on the caller's loop and may block it (#1090). Nornir.run with AsyncioRunner can emit
global task_started before the runner rejects it, but emits no host events.
