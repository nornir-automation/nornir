import logging
import traceback
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.result import MultiResult, Result

if TYPE_CHECKING:
    from nornir.core import Nornir
    from nornir.core.inventory import Host

logger = logging.getLogger("nornir")

TaskFuncType = Callable[..., Result]


class Task(object):
    """
    A task is basically a wrapper around a function that has to be run against multiple devices.
    You won't probably have to deal with this class yourself as
    :meth:`nornir.core.Nornir.run` will create it automatically.

    Arguments:
        task (callable): function or callable we will be calling
        name (``string``): name of task, defaults to ``task.__name__``
        severity_level (logging.LEVEL): Severity level associated to the task
        **kwargs: Parameters that will be passed to the ``task``

    Attributes:
        task (callable): function or callable we will be calling
        name (``string``): name of task, defaults to ``task.__name__``
        params: Parameters that will be passed to the ``task``.
        host (:obj:`nornir.core.inventory.Host`): Host we are operating with. Populated right
          before calling the ``task``
        nornir(:obj:`nornir.core.Nornir`): Populated right before calling
          the ``task``
        severity_level (logging.LEVEL): Severity level associated to the task
    """
    __slots__ = "name", "nornir", "task", "params", "severity_level"

    def __init__(
        self,
        task: TaskFuncType,
        nornir: "Nornir",
        name: Optional[str] = None,
        severity_level: int = logging.INFO,
        **kwargs: Dict[str, Any]
    ) -> None:
        self.name: str = name or task.__name__
        self.nornir: "Nornir" = nornir
        self.task: TaskFuncType = task
        self.params: Dict[str, Any] = kwargs
        self.severity_level: int = severity_level

    def __repr__(self) -> str:
        return self.name

    def start(self, host: "Host") -> MultiResult:
        """
        Run the task for the given host.

        Arguments:
            host (:obj:`nornir.core.inventory.Host`): Host we are operating with. Populated right
              before calling the ``task``
            nornir(:obj:`nornir.core.Nornir`): Populated right before calling
              the ``task``

        Returns:
            host (:obj:`nornir.core.result.MultiResult`): Results of the task and its subtasks
        """
        host_task = HostTask(self, host, self.nornir)
        try:
            logger.info("{}: {}: running task".format(host.name, self.name))
            r = self.task(host_task, **self.params)
            if not isinstance(r, Result):
                r = Result(host=host, result=r)

        except NornirSubTaskError as e:
            tb = traceback.format_exc()
            logger.error("{}: {}".format(host, tb))
            r = Result(host, exception=e, result=str(e), failed=True)

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("{}: {}".format(host, tb))
            r = Result(host, exception=e, result=tb, failed=True)

        r.name = self.name
        r.severity_level = logging.ERROR if r.failed else self.severity_level

        host_task.results.insert(0, r)
        return host_task.results

    def is_dry_run(self, override: Optional[bool] = None):
        """
        Returns whether current task is a dry_run or not.

        Arguments:
            override (bool): Override for current task
        """
        return override if override is not None else self.nornir.dry_run


class HostTask(object):
    __slots__ = "task", "host", "nornir", "results"

    def __init__(self, task: Task, host: "Host", nornir: "Nornir") -> None:
        self.task: Task = task
        self.host: Host = host
        self.nornir: Nornir = nornir
        self.results: MultiResult = MultiResult(task.name)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self.task, attr)

    def run(self, task: TaskFuncType, **kwargs) -> MultiResult:
        """
        This is a utility method to call a task from within a task. For instance:

            def grouped_tasks(task):
                task.run(my_first_task)
                task.run(my_second_task)

            nornir.run(grouped_tasks)

        This method will ensure the subtask is run only for the host in the current thread.
        """
        if not self.host or not self.nornir:
            msg = (
                "You have to call this after setting host and nornir attributes. ",
                "You probably called this from outside a nested task",
            )
            raise Exception(msg)

        if "severity_level" not in kwargs:
            kwargs["severity_level"] = self.severity_level
        t = Task(task, self.nornir, **kwargs)
        r = t.start(self.host)
        self.results.append(r[0] if len(r) == 1 else r)

        if r.failed:
            # Without this we will keep running the grouped task
            raise NornirSubTaskError(task=task, result=r)

        return r
