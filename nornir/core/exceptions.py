from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nornir.core.connection import Connection
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


class NornirNoValidInventoryError(Exception):
    """Raised when :meth:`nornir.plugins.inventory.parse` cannot load a valid inventory."""


class ConflictingConfigurationWarning(UserWarning):
    pass
