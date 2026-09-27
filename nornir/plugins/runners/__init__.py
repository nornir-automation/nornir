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

        Returns:
            Results keyed in the same order as ``hosts``.

        """
        semaphore = asyncio.Semaphore(self.num_workers)

        async def run_host(host: Host) -> MultiResult:
            async with semaphore:
                return await task.copy().astart(host)

        children = [asyncio.create_task(run_host(host)) for host in hosts]
        aggregate = asyncio.gather(*children)
        try:
            await asyncio.wait((aggregate,))
            host_results = aggregate.result()
        except BaseException:
            for child in children:
                if not child.done():
                    child.cancel()

            drain = asyncio.gather(*children, return_exceptions=True)
            while not drain.done():
                try:
                    await asyncio.shield(drain)
                except asyncio.CancelledError:
                    continue

            if aggregate.done() and not aggregate.cancelled():
                aggregate.exception()
            raise

        result = AggregatedResult(task.name)
        for host, host_result in zip(hosts, host_results, strict=True):
            result[host.name] = host_result
        return result
