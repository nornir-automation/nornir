import logging
from builtins import super

from brigade.core.exceptions import BrigadeExecutionError

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
        brigade(:obj:`brigade.core.Brigade`): Populated right before calling
          the ``task``
        dry_run(``bool``): Populated right before calling the ``task``
    """

    def __init__(self, task, **kwargs):
        self.task = task
        self.params = kwargs

    def __repr__(self):
        return self.task.__name__

    def _start(self, host, brigade, dry_run):
        self.host = host
        self.brigade = brigade
        self.dry_run = dry_run
        return self.task(self, **self.params)


class Result(object):
    """
    Returned by tasks.

    Arguments:
        changed (bool): ``True`` if the task is changing the system
        diff (obj): Diff between state of the system before/after running this task
        result (obj): Result of the task execution, see task's documentation for details
        host (:obj:`brigade.core.inventory.Host`): Reference to the host that lead ot this result

    Attributes:
        changed (bool): ``True`` if the task is changing the system
        diff (obj): Diff between state of the system before/after running this task
        result (obj): Result of the task execution, see task's documentation for details
        host (:obj:`brigade.core.inventory.Host`): Reference to the host that lead ot this result
    """

    def __init__(self, host, result=None, changed=False, diff="", **kwargs):
        self.result = result
        self.host = host
        self.changed = changed
        self.diff = diff

        for k, v in kwargs.items():
            setattr(self, k, v)


class AggregatedResult(dict):
    """
    It basically is a dict-like object that aggregates the results for all devices.
    You can access each individual result by doing ``my_aggr_result["hostname_of_device"]``.

    Attributes:
        failed_hosts (list): list of hosts that failed
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.failed_hosts = {}
        self.tracebacks = {}

    @property
    def failed(self):
        """If ``True`` at least a host failed."""
        return bool(self.failed_hosts)

    def raise_on_error(self):
        """
        Raises:
            :obj:`brigade.core.exceptions.BrigadeExecutionError`: When at least a task failed
        """
        if self.failed:
            raise BrigadeExecutionError(self)
