from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, Task


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
