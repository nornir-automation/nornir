import logging
from builtins import super
from collections import UserDict, UserList
from typing import Any, Dict, Optional

from nornir.core.exceptions import NornirExecutionError
from nornir.core.inventory import Host


class Result(object):
    """
    Result of running individual tasks.

    Arguments:
        changed: ``True`` if the task is changing the system
        diff: Diff between state of the system before/after running this task
        result: Result of the task execution, see task's documentation for details
        host: Reference to the host that lead ot this result
        failed: Whether the execution failed or not
        severity_level: Severity level associated to the result of the excecution
        exception: uncaught exception thrown during the exection of the task (if any)

    Attributes:
        changed : ``True`` if the task is changing the system
        diff: Diff between state of the system before/after running this task
        result: Result of the task execution, see task's documentation for details
        host: Reference to the host that lead to this result
        failed: Whether the execution failed or not
        severity_level: Severity level associated to the result of the excecution
        exception: uncaught exception thrown during the exection of the task (if any)
    """
    __slots__ = (
        "name",
        "host",
        "result",
        "changed",
        "diff",
        "failed",
        "exception",
        "severity_level",
        "user_defined",
    )

    def __init__(
        self,
        host: Host,
        result: Any = None,
        changed: bool = False,
        diff: str = "",
        failed: bool = False,
        exception: Optional[Exception] = None,
        severity_level: int = logging.INFO,
        **kwargs,
    ) -> None:
        self.result: Any = result
        self.host: Host = host
        self.changed: bool = changed
        self.diff: str = diff
        self.failed: bool = failed
        self.exception: Optional[Exception] = exception
        self.name: str = ""
        self.severity_level: int = severity_level
        self.user_defined = kwargs

    def __getattr__(self, attr: str) -> Any:
        try:
            return self.user_defined[attr]

        except KeyError:
            raise AttributeError(f"'{Result}' object has no attribute '{attr}'")

    def __repr__(self) -> str:
        return '{}: "{}"'.format(self.__class__.__name__, self.name)

    def __str__(self) -> str:
        if self.exception:
            return str(self.exception)

        else:
            return str(self.result)


class AggregatedResult(UserDict):
    """
    It basically is a dict-like object that aggregates the results for all devices.
    You can access each individual result by doing ``my_aggr_result["hostname_of_device"]``.
    """
    __slots__ = "name"

    def __init__(self, name: str, **kwargs) -> None:
        self.name: str = name
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return "{} ({}): {}".format(
            self.__class__.__name__, self.name, super().__repr__()
        )

    @property
    def failed(self) -> bool:
        """If ``True`` at least a host failed."""
        return any([h.failed for h in self.values()])

    @property
    def failed_hosts(self) -> Dict[str, Host]:
        """Hosts that failed during the execution of the task."""
        return {h: r for h, r in self.items() if r.failed}

    def raise_on_error(self) -> Optional[NornirExecutionError]:
        """
        Raises:
            :obj:`nornir.core.exceptions.NornirExecutionError`: When at least a task failed
        """
        if self.failed:
            raise NornirExecutionError(self)

        else:
            return None


class MultiResult(UserList):
    """
    It is basically is a list-like object that gives you access to the results of all subtasks for
    a particular device/task.
    """
    __slots__ = "name"

    def __init__(self, name: str, **kwargs) -> None:
        self.name: str = name
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return "{}: {}".format(self.__class__.__name__, super().__repr__())

    def __getattr__(self, attr: str) -> Any:
        return getattr(self[0], attr)

    @property
    def failed(self) -> bool:
        """If ``True`` at least a task failed."""
        return any([h.failed for h in self])

    @property
    def changed(self) -> bool:
        """If ``True`` at least a task changed the system."""
        return any([h.changed for h in self])

    def raise_on_error(self) -> Optional[NornirExecutionError]:
        """
        Raises:
            :obj:`nornir.core.exceptions.NornirExecutionError`: When at least a task failed
        """
        if self.failed:
            raise NornirExecutionError(self)

        else:
            return None
