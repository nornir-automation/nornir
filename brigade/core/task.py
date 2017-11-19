import logging

logger = logging.getLogger("brigade")


class Task(object):
    """
    A task is basically a wrapper around a function that has to be run against multiple devices.
    You won't probably have to deal with this class yourself as
    :meth:`brigade.core.Brigade.run` will create it automatically.

    Arguments:
        task (callable): function or callable we will be calling
        **kwargs: Parameters that will be passed to the ``task``

    Attributes:
        params: Parameters that will be passed to the ``task``.
        host (:obj:`brigade.core.inventory.Host`): Host we are operating with. Populated right
          before calling the ``task``
        inventory(:obj:`brigade.core.inventory.Inventory`): Populated right before calling
          the ``task``
        dry_run(``bool``): Populated right before calling the ``task``
    """

    def __init__(self, task, **kwargs):
        self.task = task
        self.params = kwargs

    def __repr__(self):
        return self.__class__.__name__

    def _start(self, host, inventory, dry_run):
        self.host = host
        self.inventory = inventory
        self.dry_run = dry_run
        return self.task(self, **self.params)
