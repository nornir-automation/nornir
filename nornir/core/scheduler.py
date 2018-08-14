from multiprocessing.dummy import Pool
from typing import List

from nornir.core.inventory import Host
from nornir.core.result import AggregatedResult
from nornir.core.task import Task


class TaskScheduler(object):
    """
    The TaskScheduler is responsible of running a task over the specified hosts.

    Args:
        task: Task to run
        hosts: Hosts to run on
    """

    def __init__(self, task: Task, hosts: List[Host]) -> None:
        self.task = task
        self.hosts = hosts

    def run_serial(self) -> AggregatedResult:
        """
        Run the task on the host serially

        Returns:
            The aggregated result
        """
        result = AggregatedResult(self.task.name)
        for host in self.hosts:
            result[host.name] = self.task.start(host)
        return result

    def run_parallel(self, num_workers: int) -> AggregatedResult:
        """
        Run the task on the hosts in parallel using ``num_workers`` threads

        Returns:
            The aggregated result
        """
        result = AggregatedResult(self.task.name)

        pool = Pool(processes=num_workers)
        result_pool = {
            h: pool.apply_async(self.task.start, args=(h,)) for h in self.hosts
        }
        pool.close()
        pool.join()

        for h, rp in result_pool.items():
            r = rp.get()
            result[h.name] = r
        return result
