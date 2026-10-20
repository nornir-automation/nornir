from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING

from nornir.core.exceptions import RunnerNotSyncError
from nornir.core.inventory import Host
from nornir.core.run import RunContext, RunOptions
from nornir.core.task import AggregatedResult, MultiResult, Task

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from nornir.core.plugins.runners import CancellationDepth


class SerialRunner:
    """Runner that executes the task over each host sequentially without parallelization.

    Every task runs on the caller's thread, so a debugger breakpoint inside a task works.
    It supports :meth:`nornir.core.Nornir.run_stream` but not background runs.

    Arguments:
        per_host_timeout: Seconds each host may run, checked at the task's checkpoints
        timeout: Seconds the whole run may take, checked at checkpoints and before each host

    """

    cancellation_depth: CancellationDepth = "checkpoint"
    supports_background = False

    def __init__(self, per_host_timeout: float | None = None, timeout: float | None = None) -> None:
        self.run_options = RunOptions(per_host_timeout, timeout)

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the task against each host, one after the other.

        A host whose task raises does not stop the ones after it: the exception is
        recorded in that host's result instead of propagating.

        Arguments:
            task: Task to run. Each host gets its own copy of it
            hosts: Hosts to run the task against

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: The results, keyed by host name.

        """
        run = RunContext(task, hosts, self.run_options)
        for _ in self.execute(task, hosts, run):
            pass
        return run.aggregated()

    def execute(self, task: Task, hosts: list[Host], run: RunContext) -> Iterator[None]:
        """Run the hosts one after the other on the current thread.

        Yields after each partial result of a top-level task and after each host, so that
        a stream consumed on the same thread receives events while the run progresses.
        """
        for host in hosts:
            yield from run.step_host(task.copy(), host)
            yield


class _ThreadedRun:
    """Coordinator of one threaded run. Its lock is never held while calling into the run."""

    def __init__(self, run: RunContext, num_workers: int) -> None:
        self.run = run
        self.pool = ThreadPoolExecutor(num_workers)
        self.futures: list[Future[MultiResult]] = []
        self.condition = threading.Condition()
        self.dirty = False
        self.done = 0
        options = run.options
        self.deadlines = options.per_host_timeout is not None or options.timeout is not None

    def notify(self) -> None:
        with self.condition:
            self.dirty = True
            self.condition.notify()

    def future_done(self, _future: Future[MultiResult]) -> None:
        with self.condition:
            self.done += 1
            self.dirty = True
            self.condition.notify()

    def cancel_queued(self) -> None:
        for future in self.futures:
            future.cancel()
        self.notify()

    def start(self, task: Task, hosts: list[Host]) -> None:
        for host in hosts:
            future = self.pool.submit(self.run.start_host, task.copy(), host)
            future.add_done_callback(self.future_done)
            self.futures.append(future)
        self.run.add_cancel_callback(self.cancel_queued)
        if self.deadlines:
            self.run.add_change_callback(self.notify)

    def wait(self) -> None:
        """Wait until every host is recorded, or every worker is done."""
        while not self.run.finished:
            timeout = self._timeout()
            with self.condition:
                if self.done == len(self.futures):
                    return
                if not self.dirty:
                    self.condition.wait(timeout)
                self.dirty = False
            if self.deadlines:
                self.run.expire()

    def _timeout(self) -> float | None:
        if not self.deadlines:
            return None
        deadline = self.run.next_deadline()
        return None if deadline is None else max(0.0, deadline - time.monotonic())

    def raise_worker_error(self) -> None:
        """Raise the first error a worker raised outside its task, in host order."""
        for future in self.futures:
            if future.done() and not future.cancelled():
                error = future.exception()
                if error is not None:
                    raise error


class ThreadedRunner:
    """Runner that executes the task over each host using threads.

    Cancellation and deadlines are delivered at the task's checkpoints. When a deadline
    passes, the host is recorded and the run moves on; a thread blocked in a call keeps
    its worker slot until the call returns.

    Arguments:
        num_workers: number of threads to use
        per_host_timeout: Seconds each host may run, counted from the moment it starts
        timeout: Seconds the whole run may take

    """

    cancellation_depth: CancellationDepth = "checkpoint"
    supports_background = True

    def __init__(
        self,
        num_workers: int = 20,
        per_host_timeout: float | None = None,
        timeout: float | None = None,
    ) -> None:
        self.num_workers = num_workers
        self.run_options = RunOptions(per_host_timeout, timeout)

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the task against the hosts, ``num_workers`` of them at a time.

        The call returns once every host is done or past its deadline. A host whose task
        raises does not affect the others: the exception is recorded in that host's result
        instead of propagating.

        Arguments:
            task: Task to run. Each host gets its own copy of it
            hosts: Hosts to run the task against

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: The results, keyed by host name.

        """
        run = RunContext(task, hosts, self.run_options)
        for _ in self.execute(task, hosts, run):
            pass
        return run.aggregated()

    def execute(self, task: Task, hosts: list[Host], run: RunContext) -> Iterator[None]:
        """Run the hosts on a thread pool and wait until every host is recorded."""
        self._coordinate(task, hosts, run)
        yield from ()

    def _coordinate(self, task: Task, hosts: list[Host], run: RunContext) -> None:
        coordinator = _ThreadedRun(run, self.num_workers)
        finished_normally = False
        try:
            coordinator.start(task, hosts)
            coordinator.wait()
            finished_normally = True
        finally:
            # On an interruption of the caller (Ctrl-C), queued hosts keep running as before.
            coordinator.pool.shutdown(wait=False, cancel_futures=finished_normally)
        coordinator.raise_worker_error()


class AsyncioRunner:
    """Runner that executes asynchronous tasks on the caller's event loop.

    Cancellation and deadlines interrupt a host at the call it is awaiting.

    Arguments:
        num_workers: Maximum number of hosts in flight at once
        per_host_timeout: Seconds each host may run, counted from the moment it starts
        timeout: Seconds the whole run may take

    """

    cancellation_depth: CancellationDepth = "immediate"

    def __init__(
        self,
        num_workers: int = 20,
        per_host_timeout: float | None = None,
        timeout: float | None = None,
    ) -> None:
        if isinstance(num_workers, bool) or not isinstance(num_workers, int):
            msg = "num_workers must be an integer"
            raise TypeError(msg)
        if num_workers <= 0:
            msg = "num_workers must be positive"
            raise ValueError(msg)
        self.num_workers = num_workers
        self.run_options = RunOptions(per_host_timeout, timeout)

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Reject synchronous execution regardless of the task or host list.

        Raises:
            RunnerNotSyncError: Always, because this runner only supports asynchronous execution.

        """
        raise RunnerNotSyncError(type(self).__name__)

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run one task copy per host with bounded concurrency and ordered results.

        Returns:
            Results keyed in the same order as ``hosts``.

        """
        run = RunContext(task, hosts, self.run_options)
        await self.aexecute(task, hosts, run)
        return run.aggregated()

    async def aexecute(self, task: Task, hosts: list[Host], run: RunContext) -> None:
        """Run one task copy per host on the running loop until every host is recorded.

        If the coroutine awaiting this method is cancelled, every host still running is
        cancelled and drained, nothing more is recorded, and the cancellation propagates.
        """
        coordinator = _AsyncioRun(run, self.num_workers)
        coordinator.start(task, hosts)
        try:
            await coordinator.wait()
        except BaseException:
            await coordinator.drain()
            raise


class _AsyncioRun:
    """Coordinator of one asyncio run, on the loop that runs it."""

    def __init__(self, run: RunContext, num_workers: int) -> None:
        self.run = run
        self.loop = asyncio.get_running_loop()
        self.semaphore = asyncio.Semaphore(num_workers)
        self.children: dict[str, asyncio.Task[None]] = {}
        self.waker: asyncio.Future[None] = self.loop.create_future()
        self.remaining = 0
        self.errors: list[BaseException] = []
        options = run.options
        self.deadlines = options.per_host_timeout is not None or options.timeout is not None

    def start(self, task: Task, hosts: list[Host]) -> None:
        for host in hosts:
            child = asyncio.create_task(self._run_host(task.copy(), host))
            child.add_done_callback(self._child_done)
            self.children[host.name] = child
        self.remaining = len(self.children)
        self.run.add_cancel_callback(self._from_any_thread(self._cancel_running))
        if self.deadlines:
            self.run.add_change_callback(self._from_any_thread(self._wake))

    async def _run_host(self, task: Task, host: Host) -> None:
        async with self.semaphore:
            await self.run.astart_host(task, host)

    def _from_any_thread(self, callback: Callable[[], None]) -> Callable[[], object]:
        return lambda: self.loop.call_soon_threadsafe(callback)

    def _wake(self) -> None:
        if not self.waker.done():
            self.waker.set_result(None)

    def _child_done(self, child: asyncio.Task[None]) -> None:
        self.remaining -= 1
        error = None if child.cancelled() else child.exception()
        if error is not None:
            self.errors.append(error)
        self._wake()

    def _cancel(self, hosts: list[Host]) -> None:
        for host in hosts:
            child = self.children[host.name]
            if not child.done():
                child.cancel()

    def _cancel_running(self) -> None:
        self._cancel(self.run.running_hosts())

    def _timeout(self) -> float | None:
        if not self.deadlines:
            return None
        deadline = self.run.next_deadline()
        return None if deadline is None else max(0.0, deadline - time.monotonic())

    async def wait(self) -> None:
        """Wait until every host is recorded, then cancel and wait for any leftover child."""
        while self.remaining and not self.run.finished and not self.errors:
            await asyncio.wait((self.waker,), timeout=self._timeout())
            if self.waker.done():
                self.waker = self.loop.create_future()
            if self.deadlines:
                self._cancel(self.run.expire())
        if self.errors:
            raise self.errors[0]
        stragglers = [child for child in self.children.values() if not child.done()]
        for child in stragglers:
            child.cancel()
        if stragglers:
            await asyncio.wait(stragglers)

    async def drain(self) -> None:
        """Cancel every child once and wait for all of them, even if cancelled again."""
        for child in self.children.values():
            if not child.done():
                child.cancel()
        drain = asyncio.gather(*self.children.values(), return_exceptions=True)
        while not drain.done():
            try:
                await asyncio.shield(drain)
            except asyncio.CancelledError:
                continue
