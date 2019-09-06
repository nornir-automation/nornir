from typing import List

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

from typing_extensions import Protocol


class Processor(Protocol):
    """
    This defines the Processor interface. A processor plugin needs to implement each method with the
    same exact signature. It's not necessary to subclass it.

    A processor is a plugin that gets called when certain events happen.
    """

    def task_started(self, task: Task) -> None:
        """
        This method is called right before starting the task
        """
        raise NotImplementedError("needs to be implemented by the processor")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """
        This method is called when all the hosts have completed executing their respective task
        """
        raise NotImplementedError("needs to be implemented by the processor")

    def host_started(self, task: Task, host: Host, is_subtask: bool) -> None:
        """
        This method is called before a host starts executing its instance of the task
        """
        raise NotImplementedError("needs to be implemented by the processor")

    def host_completed(
        self, task: Task, host: Host, result: MultiResult, is_subtask: bool
    ) -> None:
        """
        This method is called when a host completes its instance of a task
        """
        raise NotImplementedError("needs to be implemented by the processor")


class Processors(List[Processor]):
    """
    Processors is a wrapper class that holds a list of Processor. Each method
    will just iterate over all the the Processor objects in ``self`` and call
    its method. For instance::

        >>>    def my_method(...):
        >>>        for p in self:
        >>>            p.my_method(...)
    """

    def task_started(self, task: Task) -> None:
        for p in self:
            p.task_started(task)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        for p in self:
            p.task_completed(task, result)

    def host_started(self, task: Task, host: Host, is_subtask: bool) -> None:
        for p in self:
            p.host_started(task, host, is_subtask)

    def host_completed(
        self, task: Task, host: Host, result: MultiResult, is_subtask: bool
    ) -> None:
        for p in self:
            p.host_completed(task, host, result, is_subtask)
