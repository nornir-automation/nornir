from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from nornir.core.exceptions import RunnerNotSyncError
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task


class SerialRunner:
    """Runner that executes the task over each host sequentially without parallelization."""

    def __init__(self) -> None:
        pass

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
        result = AggregatedResult(task.name)
        for host in hosts:
            result[host.name] = task.copy().start(host)
        return result


class ThreadedRunner:
    """Runner that executes the task over each host using threads.

    Arguments:
        num_workers: number of threads to use

    """

    def __init__(self, num_workers: int = 20) -> None:
        self.num_workers = num_workers

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the task against the hosts, ``num_workers`` of them at a time.

        The call returns once every host is done. A host whose task raises does not
        affect the others: the exception is recorded in that host's result instead of
        propagating.

        Arguments:
            task: Task to run. Each host gets its own copy of it
            hosts: Hosts to run the task against

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: The results, keyed by host name.

        """
        result = AggregatedResult(task.name)
        futures = []
        with ThreadPoolExecutor(self.num_workers) as pool:
            for host in hosts:
                future = pool.submit(task.copy().start, host)
                futures.append(future)

        for future in futures:
            worker_result = future.result()
            result[worker_result.host.name] = worker_result
        return result


class AsyncioRunner:
    """Runner that executes asynchronous tasks on the caller's event loop."""

    def __init__(self, num_workers: int = 20) -> None:
        if isinstance(num_workers, bool) or not isinstance(num_workers, int):
            msg = "num_workers must be an integer"
            raise TypeError(msg)
        if num_workers <= 0:
            msg = "num_workers must be positive"
            raise ValueError(msg)
        self.num_workers = num_workers

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Reject synchronous execution regardless of the task or host list.

        Raises:
            RunnerNotSyncError: Always, because this runner only supports asynchronous execution.

        """
        raise RunnerNotSyncError(type(self).__name__)

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run one task copy per host with bounded concurrency and ordered results.

        Every host finishes before an error that escaped one host, for example from a
        processor hook, is raised, as :class:`ThreadedRunner` behaves. Only a
        cancellation by the caller interrupts the hosts still running.

        Returns:
            Results keyed in the same order as ``hosts``.

        Raises:
            asyncio.CancelledError: the caller cancelled the run; every host was
                cancelled and awaited first, and no result is returned

        """
        semaphore = asyncio.Semaphore(self.num_workers)
        cancelling_children = False

        async def run_host(host: Host) -> MultiResult:
            async with semaphore:
                host_task = task.copy()
                try:
                    return await host_task.astart(host)
                except asyncio.CancelledError as error:
                    if cancelling_children:
                        raise
                    # Nobody cancelled this host: the task raised CancelledError itself.
                    return host_task._record_unrequested_cancellation(host, error)

        children = [asyncio.create_task(run_host(host)) for host in hosts]
        # Every host finishes before a host error is raised, as ThreadedRunner does;
        # only a cancellation from the caller interrupts the hosts still running.
        aggregate = asyncio.gather(*children, return_exceptions=True)
        try:
            await asyncio.wait((aggregate,))
        except asyncio.CancelledError:
            cancelling_children = True
            await _cancel_and_drain(children, aggregate)
            raise

        return _collect(task, hosts, aggregate.result())


async def _cancel_and_drain(
    children: list[asyncio.Task[MultiResult]],
    aggregate: asyncio.Future[list[MultiResult | BaseException]],
) -> None:
    """Cancel the unfinished hosts once and wait for all of them to finish cleaning up."""
    for child in children:
        if not child.done():
            child.cancel()

    drain = asyncio.gather(*children, return_exceptions=True)
    while not drain.done():
        try:
            await asyncio.shield(drain)
        except asyncio.CancelledError:
            # A repeated caller cancellation must not interrupt the hosts' cleanup.
            continue

    if aggregate.done() and not aggregate.cancelled():
        aggregate.exception()


def _collect(
    task: Task, hosts: list[Host], host_results: list[MultiResult | BaseException]
) -> AggregatedResult:
    """Build the aggregated result in host order.

    Returns:
        The results keyed by host name.

    Raises:
        BaseException: the first error that escaped a host, re-raised unchanged

    """
    result = AggregatedResult(task.name)
    for host, host_result in zip(hosts, host_results, strict=True):
        if isinstance(host_result, BaseException):
            raise host_result
        result[host.name] = host_result
    return result
