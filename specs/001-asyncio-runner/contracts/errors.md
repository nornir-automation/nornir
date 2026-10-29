# Contract: named errors

**Feature**: 001-asyncio-runner | Target: `nornir/core/exceptions.py`

## Execution-mode mismatches

The following seven exceptions derive from `SyncAsyncMismatchError(Exception)`. Each
stores its constructor argument as an attribute and names the supported alternative.
The three connection-related ones (ConnectionPluginNotAsyncError,
ConnectionPluginNotSyncError, ConnectionModeMismatchError) also derive from the
existing `ConnectionException`, with SyncAsyncMismatchError first in their bases and
`connection` set to the connection name.

| Class | Argument | Raised at | Message guidance |
|---|---|---|---|
| SyncTaskOnAsyncRunError | task_name: str | Nornir.arun / Task.arun given a non-coroutine task | Define async def or use a sync runner; include follow-up issue URL |
| AsyncTaskOnSyncRunError | task_name: str | Nornir.run / Task.run given a coroutine task | await nr.arun / await task.arun, or define a synchronous task |
| RunnerNotSyncError | runner_name: str | AsyncioRunner.run, including sync cleanup/context exit | await nr.arun, await nr.aclose_connections, async with nr |
| RunnerNotAsyncError | runner_name: str | Nornir.arun on a runner without coroutine arun | nr.run, nr.close_connections, with nr, or select asyncio |
| ConnectionPluginNotAsyncError | connection_name: str | Host.aget_connection / aopen_connection on legacy or declared sync-only plugin | Plugin does not declare asyncio support; use get_connection from a sync task |
| ConnectionPluginNotSyncError | connection_name: str | Host.get_connection / open_connection / close_connection on declared asyncio-only plugin | Use aget_connection / aopen_connection / aclose_connection |
| ConnectionModeMismatchError | connection_name: str, opened_in: ConnectionCapability, requested: ConnectionCapability | Host.get_connection or close_connection on an asyncio-bound connection; Host.aget_connection on a sync-bound connection | Connection is open in `opened_in` mode; use the matching get, or close it with the matching close method before reopening it in `requested` mode |

Top-level mismatch checks precede host execution; subtask checks precede child execution
and child events; connection checks precede opening or returning an incompatible
transport, including cache hits. Parent events may already exist for subtask/connection
calls. An uncaught mismatch in user task code becomes a failed parent result through
normal exception handling. A close mismatch must not remove the cached connection.

For a cached connection the capability check precedes the mode check: a plugin lacking
the requested capability raises ConnectionPluginNotAsyncError or
ConnectionPluginNotSyncError; a dual plugin open in the other mode raises
ConnectionModeMismatchError. The bound mode comes from the Host's capability metadata,
never from plugin attributes.

```python
SYNC_TASKS_IN_ASYNC_RUNS_ISSUE = "https://github.com/nornir-automation/nornir/issues/1120"
```

The constant points to the follow-up issue on synchronous tasks in async runs.

## Registry and contract validation

These errors are separate from execution-mode mismatches; changing the calling mode
does not repair an ambiguous registry or malformed plugin.

| Class / base | Constructor | Conditions | Message guidance |
|---|---|---|---|
| ConnectionPluginAmbiguousError(ConnectionException) | connection_name: str | Name exists in both registries, even for the same class | Name both registries; remove one registration or rename the plugin |
| ConnectionPluginContractError(ConnectionException) | connection_name: str, reason: str | Invalid reporting method/declaration, missing declared operation, or conflicting internal cache ownership | Name the plugin and failed contract requirement |

Both are raised before opening. Get/open checks current cross-registry ambiguity even
for a cached name. Cleanup uses recorded ownership and can close connections despite
registry ambiguity or deregistration. Invalid reporting results must not be coerced
into a valid capability declaration; report the contract error with the original
exception chained if the reporting method failed.

Existing errors are reused unchanged: PluginNotRegistered, PluginAlreadyRegistered,
ConnectionAlreadyOpen, ConnectionNotOpen, NornirSubTaskError, NornirExecutionError.
Same-registry registration keeps existing idempotency rules. New AsyncioRunner argument
validation uses TypeError for non-integers/booleans and ValueError for nonpositive integers.

## Precedence

Task entry points check task kind before runner support. Get/open checks cross-registry
ambiguity first, then pending/existing state; explicit open of an existing or opening
name raises ConnectionAlreadyOpen, a synchronous get of an opening name raises it too,
and an asynchronous get of an opening name waits for the open and then applies the
cache-hit checks. For a new capability instance, validate its entire declaration
and all declared operations before checking the requested mode. A valid plugin lacking
the requested mode raises the appropriate mismatch rather than a contract error.

## Host errors and cancellation in AsyncioRunner

An exception that escapes one host's execution without becoming that host's result
(for example a processor hook raising) does not interrupt the other hosts: the runner
waits for every host and then raises the first such exception in host order, as
ThreadedRunner does. A `CancelledError` raised by a task's own code while the asyncio
task is not being cancelled becomes that host's failed result and never reaches the
caller. Only a caller cancellation of `arun` cancels in-flight hosts; it propagates as
CancelledError after the owned futures are drained, with no aggregate returned.
Bulk cleanup, synchronous or asynchronous, attempts every connection and raises the
first error afterwards; the others are discarded (follow-up: exception groups).
