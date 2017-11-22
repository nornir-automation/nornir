import concurrent.futures
import logging

from brigade.core.exceptions import BrigadeExecutionException
from brigade.core.task import Task


logger = logging.getLogger("brigade")


class Brigade(object):
    """
    This is the main object to work with. It contains the inventory and it serves
    as task dispatcher.

    Arguments:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
        num_workers(``int``): How many hosts run in parallel

    Attributes:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
        num_workers(``int``): How many hosts run in parallel
    """

    def __init__(self, inventory, dry_run, num_workers=5):
        """
        Args:
            inventory(brigade.core.inventory.Inventory): An Inventory object.
            dry_run(bool): Whether this is a dry run or not.
        """
        self.inventory = inventory
        self.dry_run = dry_run
        self.num_workers = num_workers

    def filter(self, **kwargs):
        """
        See :py:meth:`brigade.core.inventory.Inventory.filter`

        Returns:
            :obj:`Brigade`: A new object with same configuration as ``self`` but filtered inventory.
        """
        return Brigade(inventory=self.inventory.filter(**kwargs),
                       dry_run=self.dry_run, num_workers=self.num_workers)

    def _run_single_thread(self, task, **kwargs):
        exception = False
        result = {}
        for host in self.inventory.hosts.values():
            try:
                r = task._start(host=host, brigade=self, dry_run=self.dry_run)
            except Exception as e:
                exception = True
                r = e
            result[host.name] = r
        if exception:
            raise BrigadeExecutionException(result)
        return result

    def _run_multithread(self, task, **kwargs):
        exception = False
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            tasks = {executor.submit(task._start,
                                     host=host, brigade=self, dry_run=self.dry_run): host
                     for host in self.inventory.hosts.values()}
            result = {}
            for t in concurrent.futures.as_completed(tasks):
                host = tasks[t]
                try:
                    r = t.result()
                except Exception as e:
                    exception = True
                    r = e
                result[host.name] = r
        if exception:
            raise BrigadeExecutionException(result)
        return result

    def run(self, task, **kwargs):
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            dict: dict where keys are hostnames and values are each individual result

        Raises:
            :obj:`brigade.core.exceptions.BrigadeExecutionException`: If any task raises an
              Exception
        """
        t = Task(task, **kwargs)
        if self.num_workers == 1:
            return self._run_single_thread(t, **kwargs)
        else:
            return self._run_multithread(t, **kwargs)
