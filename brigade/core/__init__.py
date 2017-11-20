import itertools
import logging
from multiprocessing import Pool

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

    def run(self, task, **kwargs):
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            dict: dict where keys are hostnames and values are each individual result
        """
        self.last_task = Task(task, **kwargs)
        if self.num_workers > 1:

            pool = Pool(processes=self.num_workers)
            result = pool.map(run_task, itertools.izip(self.inventory.hosts.values(),
                                                       itertools.repeat(self)))
            pool.close()
            pool.join()
        else:
            result = [run_task((h, self)) for h in self.inventory.hosts.values()]
        return {r[0]: r[1] for r in result}


def run_task(args):
    host = args[0]
    brigade = args[1]
    logger.debug("{}: running task {}".format(host.name, brigade.last_task.task))
    try:
        return host.name, brigade.last_task._start(host, brigade=brigade, dry_run=brigade.dry_run)
    except Exception as e:
        logger.error("{}: {}".format(host, e.message))
        raise
