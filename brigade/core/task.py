from builtins import super

from brigade.core.exceptions import BrigadeExecutionError


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

    def __init__(self, task, name=None, **kwargs):
        self.name = name or task.__name__
        self.task = task
        self.params = kwargs

    def __repr__(self):
        return self.name

    def _start(self, host, brigade, dry_run):
        self.host = host
        self.brigade = brigade
        self.dry_run = dry_run if dry_run is not None else brigade.dry_run
        return self.task(self, **self.params) or Result(host)

    def run(self, task, dry_run=None, **kwargs):
        """
        This is a utility method to call a task from within a task. For instance:

            def grouped_tasks(task):
                task.run(my_first_task)
                task.run(my_second_task)

            brigade.run(grouped_tasks)

        This method will ensure the subtask is run only for the host in the current thread.
        """
        if not self.host or not self.brigade:
            msg = ("You have to call this after setting host and brigade attributes. ",
                   "You probably called this from outside a nested task")
            raise Exception(msg)
        return Task(task, **kwargs)._start(self.host, self.brigade, dry_run)


class Result(object):
    """
    Returned by tasks.

    Arguments:
        changed (bool): ``True`` if the task is changing the system
        diff (obj): Diff between state of the system before/after running this task
        result (obj): Result of the task execution, see task's documentation for details
        host (:obj:`brigade.core.inventory.Host`): Reference to the host that lead ot this result
        failed (bool): Whether the execution failed or not
        exception (Exception): uncaught exception thrown during the exection of the task (if any)

    Attributes:
        changed (bool): ``True`` if the task is changing the system
        diff (obj): Diff between state of the system before/after running this task
        result (obj): Result of the task execution, see task's documentation for details
        host (:obj:`brigade.core.inventory.Host`): Reference to the host that lead ot this result
        failed (bool): Whether the execution failed or not
        exception (Exception): uncaught exception thrown during the exection of the task (if any)
    """

    def __init__(self, host, result=None, changed=False, diff="", failed=False, exception=None,
                 **kwargs):
        self.result = result
        self.host = host
        self.changed = changed
        self.diff = diff
        self.failed = failed
        self.exception = exception

        for k, v in kwargs.items():
            setattr(self, k, v)


class AggregatedResult(dict):
    """
    It basically is a dict-like object that aggregates the results for all devices.
    You can access each individual result by doing ``my_aggr_result["hostname_of_device"]``.

    Attributes:
        failed_hosts (list): list of hosts that failed
    """
    def __init__(self, name, **kwargs):
        self.name = name
        super().__init__(**kwargs)

    def __repr__(self):
        return '{}: {}'.format(self.__class__.__name__, self.name)

    @property
    def failed(self):
        """If ``True`` at least a host failed."""
        return any([h.failed for h in self.values()])

    def raise_on_error(self):
        """
        Raises:
            :obj:`brigade.core.exceptions.BrigadeExecutionError`: When at least a task failed
        """
        if self.failed:
            raise BrigadeExecutionError(self)
