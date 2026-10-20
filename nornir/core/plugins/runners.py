from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol

from nornir.core.inventory import Host
from nornir.core.plugins.register import PluginRegister
from nornir.core.task import AggregatedResult, Task

if TYPE_CHECKING:
    from collections.abc import Iterator

    from nornir.core.run import RunContext, RunOptions

RUNNERS_PLUGIN_PATH = "nornir.plugins.runners"


class RunnerPlugin(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the plugin."""
        raise NotImplementedError("needs to be implemented by the plugin")

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the given task over all the hosts."""
        raise NotImplementedError("needs to be implemented by the plugin")


class AsyncRunnerPlugin(Protocol):
    """Interface for runners that execute tasks on the caller's event loop."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the plugin."""
        raise NotImplementedError("needs to be implemented by the plugin")

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the given task over all hosts asynchronously."""
        raise NotImplementedError("needs to be implemented by the plugin")


CancellationDepth = Literal["checkpoint", "immediate"]
"""Where a runner delivers cancellation and deadlines.

``checkpoint``: at the task's next checkpoint (``task.checkpoint()``, a ``yield``, or the
start of a subtask). ``immediate``: at the call the task is currently awaiting.
"""


class StreamingRunner(Protocol):
    """Optional interface for runners that support streaming, cancellation and deadlines.

    It is a sibling of :class:`RunnerPlugin`: a runner implements both. The core creates a
    :class:`nornir.core.run.RunContext` for each run and passes it to :meth:`execute`; the
    run context records each host, delivers events and applies the deadlines, and the
    runner decides when each host starts.
    """

    @property
    def cancellation_depth(self) -> CancellationDepth:
        """Where this runner delivers cancellation and deadlines."""
        raise NotImplementedError("needs to be implemented by the plugin")

    @property
    def supports_background(self) -> bool:
        """Whether the core may drive :meth:`execute` on a thread other than the caller's.

        A runner that returns ``False`` supports ``run_stream`` but not ``submit``.
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    @property
    def run_options(self) -> RunOptions:
        """Default deadlines of this runner; per-run options override them field by field."""
        raise NotImplementedError("needs to be implemented by the plugin")

    def execute(self, task: Task, hosts: list[Host], run: RunContext) -> Iterator[None]:
        """Run ``task`` over ``hosts`` until ``run.finished``.

        This is a generator. It yields whenever the core may deliver pending events to a
        consumer running on the same thread; a runner that executes hosts on other threads
        does not need to yield at all.
        """
        raise NotImplementedError("needs to be implemented by the plugin")


class AsyncStreamingRunner(Protocol):
    """Optional interface for asynchronous runners that support streaming and cancellation.

    It is a sibling of :class:`AsyncRunnerPlugin`.
    """

    @property
    def cancellation_depth(self) -> CancellationDepth:
        """Where this runner delivers cancellation and deadlines."""
        raise NotImplementedError("needs to be implemented by the plugin")

    @property
    def run_options(self) -> RunOptions:
        """Default deadlines of this runner; per-run options override them field by field."""
        raise NotImplementedError("needs to be implemented by the plugin")

    async def aexecute(self, task: Task, hosts: list[Host], run: RunContext) -> None:
        """Run ``task`` over ``hosts`` on the running event loop until ``run.finished``."""
        raise NotImplementedError("needs to be implemented by the plugin")


RunnersPluginRegister: PluginRegister[type[RunnerPlugin]] = PluginRegister(RUNNERS_PLUGIN_PATH)
