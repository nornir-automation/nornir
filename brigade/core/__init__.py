import logging

from brigade.core.task import Task


logger = logging.getLogger("brigade")


class Brigade(object):
    """
    This is the main object to work with. It contains the inventory and it serves
    as task dispatcher.

    Arguments:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not

    Attributes:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
    """

    def __init__(self, inventory, dry_run):
        """
        Args:
            inventory(brigade.core.inventory.Inventory): An Inventory object.
            dry_run(bool): Whether this is a dry run or not.
        """
        self.inventory = inventory
        self.dry_run = dry_run

    def filter(self, **kwargs):
        """
        See :py:meth:`brigade.core.inventory.Inventory.filter`

        Returns:
            :obj:`Brigade`: A new object with same configuration as ``self`` but filtered inventory.
        """
        return Brigade(inventory=self.inventory.filter(**kwargs),
                       dry_run=self.dry_run)

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
        task = Task(task, **kwargs)
        result = {}
        for host in self.inventory.hosts.values():
            # TODO parallelize this so all of them tasks are run in parallel
            logger.debug("{}: running task {}".format(host.name, task))
            result[host.name] = task._start(host, inventory=self, dry_run=self.dry_run)
        return result
