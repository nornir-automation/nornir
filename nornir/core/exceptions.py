from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from nornir.core.connection import Connection
    from nornir.core.plugins.connections import ConnectionCapability
    from nornir.core.result import AggregatedResult, MultiResult, Result
    from nornir.core.tasks import Task


SYNC_TASKS_IN_ASYNC_RUNS_ISSUE = "https://github.com/nornir-automation/nornir/issues/1085"


class SyncAsyncMismatchError(Exception):
    """Raised when an operation is used from an unsupported execution mode."""


class SyncTaskOnAsyncRunError(SyncAsyncMismatchError):
    """Raised when an asynchronous run receives a synchronous task."""

    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        super().__init__(
            f"Task {task_name!r} is synchronous and cannot run asynchronously. "
            "Define it with 'async def' or use a synchronous runner. "
            f"See {SYNC_TASKS_IN_ASYNC_RUNS_ISSUE}."
        )


class AsyncTaskOnSyncRunError(SyncAsyncMismatchError):
    """Raised when a synchronous run receives an asynchronous task."""

    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        super().__init__(
            f"Task {task_name!r} is asynchronous and cannot run synchronously. "
            "Use 'await nr.arun(...)' or 'await task.arun(...)', or define a synchronous task."
        )


class RunnerNotSyncError(SyncAsyncMismatchError):
    """Raised when a runner does not support synchronous operations."""

    def __init__(self, runner_name: str) -> None:
        self.runner_name = runner_name
        super().__init__(
            f"Runner {runner_name!r} does not support synchronous operations. "
            "Use 'await nr.arun(...)', 'await nr.aclose_connections()', or 'async with nr'."
        )


class RunnerNotAsyncError(SyncAsyncMismatchError):
    """Raised when a runner does not support asynchronous operations."""

    def __init__(self, runner_name: str) -> None:
        self.runner_name = runner_name
        super().__init__(
            f"Runner {runner_name!r} does not support asynchronous operations. "
            "Use 'nr.run(...)', 'nr.close_connections()', or 'with nr', or select an "
            "asyncio runner."
        )


class ConnectionPluginNotAsyncError(SyncAsyncMismatchError):
    """Raised when a connection plugin does not support asyncio."""

    def __init__(self, connection_name: str) -> None:
        self.connection_name = connection_name
        super().__init__(
            f"Connection plugin {connection_name!r} does not declare asyncio support. "
            "Use 'get_connection(...)' from a synchronous task."
        )


class ConnectionPluginNotSyncError(SyncAsyncMismatchError):
    """Raised when a connection plugin does not support synchronous operations."""

    def __init__(self, connection_name: str) -> None:
        self.connection_name = connection_name
        super().__init__(
            f"Connection plugin {connection_name!r} does not declare synchronous support. "
            "Use 'aget_connection(...)', 'aopen_connection(...)', or "
            "'aclose_connection(...)'."
        )


class InventoryPluginNotSyncError(SyncAsyncMismatchError):
    """Raised when InitNornir is given an inventory plugin that only loads asynchronously."""

    def __init__(self, plugin_name: str) -> None:
        self.plugin_name = plugin_name
        super().__init__(
            f"Inventory plugin {plugin_name!r} only declares asyncio support and cannot be "
            "loaded by InitNornir(). Use 'nr = await AInitNornir(...)' instead, or ask the "
            "plugin author for synchronous support."
        )


class TransformFunctionNotSyncError(SyncAsyncMismatchError):
    """Raised when InitNornir is given a transform function defined with ``async def``."""

    def __init__(self, transform_name: str) -> None:
        self.transform_name = transform_name
        super().__init__(
            f"Transform function {transform_name!r} is defined with 'async def' and cannot "
            "be applied by InitNornir(). Use 'nr = await AInitNornir(...)' instead, or define "
            "a synchronous transform function."
        )


_MODE_METHODS: dict[str, tuple[str, str, str]] = {
    "sync": ("a synchronous", "'get_connection(...)'", "'close_connection(...)'"),
    "asyncio": ("an asyncio", "'aget_connection(...)'", "'aclose_connection(...)'"),
}


class ConnectionModeMismatchError(SyncAsyncMismatchError):
    """Raised when an open connection is used from the mode that did not open it.

    A connection is bound to the execution mode that opened it until it is closed.
    """

    def __init__(
        self,
        connection_name: str,
        opened_in: ConnectionCapability,
        requested: ConnectionCapability,
    ) -> None:
        self.connection_name = connection_name
        self.opened_in = opened_in
        self.requested = requested
        task_kind, get_method, close_method = _MODE_METHODS[opened_in]
        super().__init__(
            f"Connection {connection_name!r} is open in {opened_in} mode and was requested "
            f"in {requested} mode. Use {get_method} from {task_kind} task, or close it with "
            f"{close_method} before reopening it in {requested} mode."
        )


class ConnectionPluginAmbiguousError(Exception):
    """Raised when a connection name is registered in both plugin registries."""

    def __init__(self, connection_name: str) -> None:
        self.connection_name = connection_name
        super().__init__(
            f"Connection plugin {connection_name!r} is registered in both the legacy and "
            "capability-aware registries. Remove one registration or rename the plugin."
        )


class ConnectionPluginContractError(Exception):
    """Raised when a capability-aware connection plugin violates its contract."""

    def __init__(self, connection_name: str, reason: str) -> None:
        self.connection_name = connection_name
        self.reason = reason
        super().__init__(f"Connection plugin {connection_name!r} violates its contract: {reason}")


class InventoryPluginAmbiguousError(Exception):
    """Raised when an inventory plugin name is registered in both inventory registries."""

    def __init__(self, plugin_name: str) -> None:
        self.plugin_name = plugin_name
        super().__init__(
            f"Inventory plugin {plugin_name!r} is registered in both the legacy and "
            "capability-aware inventory registries. Remove one registration or rename "
            "the plugin."
        )


class InventoryPluginContractError(Exception):
    """Raised when a capability-aware inventory plugin violates its contract."""

    def __init__(self, plugin_name: str, reason: str) -> None:
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Inventory plugin {plugin_name!r} violates its contract: {reason}")


class TransformFunctionAmbiguousError(Exception):
    """Raised when a transform function name is registered in both transform registries."""

    def __init__(self, transform_name: str) -> None:
        self.transform_name = transform_name
        super().__init__(
            f"Transform function {transform_name!r} is registered in both the synchronous "
            "and async transform function registries. Remove one registration or rename "
            "the transform function."
        )


class ConnectionException(Exception):
    """Superclass for all the Connection* Exceptions."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection


class ConnectionAlreadyOpen(ConnectionException):
    """Raised when opening an already opened connection."""


class ConnectionNotOpen(ConnectionException):
    """Raised when trying to close a connection that isn't open."""


class PluginAlreadyRegistered(Exception):
    """Raised when trying to register an already registered plugin."""


class PluginNotRegistered(Exception):
    """Raised when trying to access a plugin that is not registered."""


class NornirExecutionError(Exception):
    """Raised by nornir when any of the tasks managed by :meth:`nornir.core.Nornir.run` fail."""

    def __init__(self, result: AggregatedResult) -> None:
        self.result = result

    @property
    def failed_hosts(self) -> dict[str, MultiResult]:
        """Hosts that failed to complete the task."""
        return {k: v for k, v in self.result.items() if v.failed}

    def __str__(self) -> str:
        text = "\n"
        for k, r in self.result.items():
            text += f"{'#' * 40}\n"
            if r.failed:
                text += f"# {k} (failed)\n"
            else:
                text += f"# {k} (succeeded)\n"
            text += f"{'#' * 40}\n"
            for sub_r in r:
                text += f"**** {sub_r.name}\n"
                text += f"{sub_r}\n"
        return text


class NornirSubTaskError(Exception):
    """Raised by nornir when a sub task managed by :meth:`nornir.core.Task.run` has failed."""

    def __init__(self, task: Task, result: Result) -> None:
        self.task = task
        self.result = result

    def __str__(self) -> str:
        return f"Subtask: {self.task} (failed)\n"


class TaskInterruptedError(BaseException):
    """Base of the errors that stop a host's task before it finishes.

    It subclasses :class:`BaseException`, like :class:`asyncio.CancelledError`, so that an
    ``except Exception`` block in a task does not stop a cancellation or a deadline.

    Arguments:
        host_name: Name of the host whose task was interrupted
        task_name: Name of the interrupted task
        started: ``False`` when the host was recorded before its task started

    """

    def __init__(self, host_name: str, task_name: str, started: bool = True) -> None:
        self.host_name = host_name
        self.task_name = task_name
        self.started = started
        super().__init__(self._message())

    def _message(self) -> str:
        return f"Task {self.task_name!r} on host {self.host_name!r} was interrupted."

    def _arguments(self) -> tuple[object, ...]:
        return (self.host_name, self.task_name, self.started)

    def __reduce__(self) -> tuple[type[TaskInterruptedError], tuple[object, ...]]:
        return (type(self), self._arguments())

    def fresh(self) -> TaskInterruptedError:
        """Return a new instance with the same fields, to raise again at a later checkpoint.

        Returns:
            The new instance, without a traceback.

        """
        return copy.copy(self)


class TaskCancelledError(TaskInterruptedError):
    """Recorded for a host whose run was cancelled before its task finished."""

    def _message(self) -> str:
        if self.started:
            return f"Task {self.task_name!r} on host {self.host_name!r} was cancelled."
        return (
            f"Task {self.task_name!r} on host {self.host_name!r} was cancelled before it "
            "started."
        )


class TaskTimeoutError(TaskInterruptedError):
    """Recorded for a host that passed its per-host deadline or the run deadline.

    Arguments:
        host_name: Name of the host whose task was interrupted
        task_name: Name of the interrupted task
        timeout: The deadline that passed, in seconds
        scope: ``"host"`` for the per-host deadline, ``"run"`` for the run deadline
        started: ``False`` when the host never started before the run deadline

    """

    def __init__(
        self,
        host_name: str,
        task_name: str,
        timeout: float,
        scope: Literal["host", "run"],
        started: bool = True,
    ) -> None:
        self.timeout = timeout
        self.scope = scope
        super().__init__(host_name, task_name, started)

    def _arguments(self) -> tuple[object, ...]:
        return (self.host_name, self.task_name, self.timeout, self.scope, self.started)

    def _message(self) -> str:
        subject = f"Task {self.task_name!r} on host {self.host_name!r}"
        if not self.started:
            return f"{subject} did not start before the run timeout of {self.timeout:g} seconds."
        if self.scope == "host":
            return f"{subject} exceeded its per-host timeout of {self.timeout:g} seconds."
        return f"{subject} exceeded the run timeout of {self.timeout:g} seconds."


class RunnerCapabilityError(Exception):
    """Raised when the configured runner does not support the requested entry point.

    Arguments:
        runner_name: Class name of the runner
        capability: The entry point that was requested: ``submit``, ``run_stream``,
            ``asubmit`` or ``astream``
        background: ``True`` when the runner supports streaming but not background runs

    """

    def __init__(self, runner_name: str, capability: str, background: bool = False) -> None:
        self.runner_name = runner_name
        self.capability = capability
        self.background = background
        if background:
            message = (
                f"{runner_name} does not support background runs ({capability!r}) because it "
                "runs every task on the caller's thread. Use 'run_stream' to consume the run "
                "live, or use ThreadedRunner."
            )
        elif capability in {"asubmit", "astream"}:
            message = (
                f"{runner_name} does not support {capability!r}. Implement "
                "AsyncStreamingRunner, or use arun()."
            )
        else:
            message = (
                f"{runner_name} does not support {capability!r}. Implement StreamingRunner, "
                "or use run()."
            )
        super().__init__(message)

    def __reduce__(self) -> tuple[type[RunnerCapabilityError], tuple[str, str, bool]]:
        return (type(self), (self.runner_name, self.capability, self.background))


class NornirNoValidInventoryError(Exception):
    """Raised when :meth:`nornir.plugins.inventory.parse` cannot load a valid inventory."""


class ConflictingConfigurationWarning(UserWarning):
    pass
