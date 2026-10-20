"""Public contracts added by feature 003; design artifact, not installed implementation.

Signatures only, checked with mypy. Concrete classes (RunContext, the handles, the
streams) are written as Protocols to state their public shape without bodies. Each
docstring names the module that will hold the class. Behaviour is specified in
../spec.md and ../research.md; entry points and errors are in entry-points.md and
errors.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator
    from types import TracebackType

CancellationDepth = Literal["checkpoint", "immediate"]
InterruptReason = Literal["cancelled", "timeout"]


class PartialResult:
    """Intermediate result of one host. Module: nornir.core.task.

    ``progress`` is None or a number between 0 and 1, otherwise ValueError.
    ``name`` is set by the driver to the name of the task that yielded it.
    There is no failed, changed or diff state.
    """

    def __init__(self, host: Host, result: Any = None, progress: float | None = None) -> None:
        self.host = host
        self.result = result
        self.progress = progress
        self.name: str | None = None


RunEvent = PartialResult | Result


@dataclass(frozen=True)
class RunOptions:
    """Per-run settings, separate from task arguments. Module: nornir.core.run.

    Each field is None or a positive finite number of seconds (ValueError otherwise).
    A None field keeps the runner's value.
    """

    per_host_timeout: float | None = None
    timeout: float | None = None


class RunContext(Protocol):
    """State of one run, shared by the core and the runner. Module: nornir.core.run.

    Thread-safe. Constructed as ``RunContext(task, hosts, options=None)``: by the core for
    the new entry points, and by a runner's own ``run()`` / ``arun()``.
    """

    @property
    def options(self) -> RunOptions:
        """Effective options: per-run values over runner values."""
        ...

    @property
    def cancelled(self) -> bool:
        """Whether cancel() was called or the run deadline passed."""
        ...

    @property
    def finished(self) -> bool:
        """Whether every selected host is recorded."""
        ...

    def start_host(self, task: Task, host: Host) -> MultiResult:
        """Run ``task`` (a fresh copy) for ``host`` on the current thread and record it.

        Returns the recorded MultiResult. If the host was already recorded (cancelled or
        expired before it started), returns that record without running anything.
        """
        ...

    def running_hosts(self) -> list[Host]:
        """Return the hosts whose task has started and is not recorded yet."""
        ...

    def completed(self) -> list[Result]:
        """Return the final top-level result of each recorded host, in completion order."""
        ...

    def aggregated(self) -> AggregatedResult:
        """Return the results of every host in selection order; RuntimeError if incomplete."""
        ...

    def step_host(self, task: Task, host: Host) -> Iterator[None]:
        """Run like start_host, but yield after each top-level PartialResult."""
        ...

    async def astart_host(self, task: Task, host: Host) -> MultiResult:
        """Run the asynchronous counterpart of start_host."""
        ...

    def cancel(self) -> None:
        """Request cancellation and record pending hosts as never started.

        Safe from any thread, any number of times.
        """
        ...

    def expire(self) -> list[Host]:
        """Record every host past its deadline, and every pending host after the run deadline.

        Returns the running hosts recorded by this call, so an immediate-depth runner
        can interrupt them.
        """
        ...

    def next_deadline(self) -> float | None:
        """Return the earliest pending deadline, as a time.monotonic() value."""
        ...

    def add_cancel_callback(self, callback: Callable[[], object]) -> None:
        """Call ``callback`` once when the run is first cancelled or its deadline passes.

        Called from the thread that cancels, or at once if already cancelled.
        """
        ...

    def add_change_callback(self, callback: Callable[[], object]) -> None:
        """Call ``callback`` when a host starts or is recorded, or the run is cancelled.

        Called with the run's lock held: it must return quickly and not call the run.
        """
        ...


class RunnerPlugin(Protocol):
    """Unchanged. Module: nornir.core.plugins.runners."""

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the given task over all the hosts."""
        ...


class AsyncRunnerPlugin(Protocol):
    """Unchanged (spec 001). Module: nornir.core.plugins.runners."""

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the given task over all hosts asynchronously."""
        ...


class StreamingRunner(Protocol):
    """Sibling of RunnerPlugin. Module: nornir.core.plugins.runners."""

    @property
    def cancellation_depth(self) -> CancellationDepth:
        """Where cancellation is delivered: at checkpoints or immediately."""
        ...

    @property
    def supports_background(self) -> bool:
        """Whether the core may drive execute() off the caller's thread."""
        ...

    def execute(self, task: Task, hosts: list[Host], run: RunContext) -> Iterator[None]:
        """Run ``task`` over ``hosts`` until run.finished.

        Yield to let the core deliver pending events to a consumer on the same thread.
        """
        ...


class AsyncStreamingRunner(Protocol):
    """Sibling of AsyncRunnerPlugin. Module: nornir.core.plugins.runners."""

    @property
    def cancellation_depth(self) -> CancellationDepth:
        """Where cancellation is delivered: at checkpoints or immediately."""
        ...

    async def aexecute(self, task: Task, hosts: list[Host], run: RunContext) -> None:
        """Run ``task`` over ``hosts`` on the running loop until run.finished."""
        ...


class ProgressProcessor(Protocol):
    """Optional sibling of Processor. Module: nornir.core.processor.

    Called for top-level tasks and subtasks; ``task`` is the task that yielded.
    A processor that does not define the method is never called with it.
    """

    def task_instance_progress(self, task: Task, host: Host, partial: PartialResult) -> None:
        """Handle a partial result reported by a host."""
        ...


class RunHandle(Protocol):
    """Background run on threads. Module: nornir.core.run."""

    @property
    def id(self) -> str:
        """The run identifier."""
        ...

    @property
    def done(self) -> bool:
        """Whether every host is recorded and the run is finalized."""
        ...

    def results(self) -> Iterator[Result]:
        """Iterate over final results in completion order, replaying finished hosts."""
        ...

    def events(self) -> Iterator[RunEvent]:
        """Iterate over the events produced after this call."""
        ...

    def progress(self) -> dict[str, PartialResult]:
        """Return the latest partial result of each host."""
        ...

    def cancel(self) -> None:
        """Cancel the run; safe from any thread, any number of times."""
        ...

    def result(self, timeout: float | None = None) -> AggregatedResult:
        """Wait for the run and return its results.

        Raises TimeoutError if ``timeout`` elapses first, and NornirExecutionError when
        raise_on_error applies and a host failed.
        """
        ...


class AsyncRunHandle(Protocol):
    """Background run on the caller's event loop. Module: nornir.core.run."""

    @property
    def id(self) -> str:
        """The run identifier."""
        ...

    @property
    def done(self) -> bool:
        """Whether every host is recorded and the run is finalized."""
        ...

    def results(self) -> AsyncIterator[Result]:
        """Iterate over final results in completion order, replaying finished hosts."""
        ...

    def events(self) -> AsyncIterator[RunEvent]:
        """Iterate over the events produced after this call."""
        ...

    def progress(self) -> dict[str, PartialResult]:
        """Return the latest partial result of each host."""
        ...

    def cancel(self) -> None:
        """Cancel the run; safe from any thread."""
        ...

    async def result(self) -> AggregatedResult:
        """Wait for the run without cancelling it when the waiter is cancelled."""
        ...


class RunStream(Protocol):
    """Returned by Nornir.run_stream(). Single-use. Module: nornir.core.run."""

    def __iter__(self) -> Iterator[RunEvent]:
        """Return a new iterator; finalizing it before the end cancels the run."""
        ...

    def __enter__(self) -> RunStream:
        """Return the stream."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Cancel the run if it has not finished."""
        ...

    def cancel(self) -> None:
        """Cancel the run."""
        ...

    def result(self) -> AggregatedResult:
        """Return the results once the run has ended."""
        ...


class AsyncRunStream(Protocol):
    """Returned by Nornir.astream(). Single-use. Module: nornir.core.run."""

    def __aiter__(self) -> AsyncIterator[RunEvent]:
        """Return a new iterator; finalizing it before the end cancels the run."""
        ...

    async def __aenter__(self) -> AsyncRunStream:
        """Return the stream."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Cancel the run if it has not finished."""
        ...

    def cancel(self) -> None:
        """Cancel the run."""
        ...

    async def result(self) -> AggregatedResult:
        """Return the results once the run has ended."""
        ...
