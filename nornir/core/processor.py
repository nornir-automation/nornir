from __future__ import annotations

from typing import Protocol

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task


class Processor(Protocol):
    """Interface that defines the Processor plugins.

    A processor plugin needs to implement each method with the same exact signature.
    It's not necessary to subclass this class.

    A processor is a plugin that gets called when certain events happen.
    """

    def task_started(self, task: Task) -> None:
        """Handle the event fired right before starting the task."""
        raise NotImplementedError("needs to be implemented by the processor")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Handle the event fired when all the hosts have completed their respective task."""
        raise NotImplementedError("needs to be implemented by the processor")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Handle the event fired before a host starts executing its instance of the task."""
        raise NotImplementedError("needs to be implemented by the processor")

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Handle the event fired when a host completes its instance of a task."""
        raise NotImplementedError("needs to be implemented by the processor")

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Handle the event fired before a host starts executing a subtask."""
        raise NotImplementedError("needs to be implemented by the processor")

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Handle the event fired when a host completes executing a subtask."""
        raise NotImplementedError("needs to be implemented by the processor")


class Processors(list[Processor]):
    """Wrapper class that holds a list of Processor objects.

    Each method will just iterate over all the Processor objects in ``self`` and call
    its method. For instance::

        >>>    def my_method(...):
        >>>        for p in self:
        >>>            p.my_method(...)
    """

    def task_started(self, task: Task) -> None:
        """Call ``task_started`` on every processor, in order."""
        for p in self:
            p.task_started(task)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Call ``task_completed`` on every processor, in order."""
        for p in self:
            p.task_completed(task, result)

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Call ``task_instance_started`` on every processor, in order."""
        for p in self:
            p.task_instance_started(task, host)

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Call ``task_instance_completed`` on every processor, in order."""
        for p in self:
            p.task_instance_completed(task, host, result)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Call ``subtask_instance_started`` on every processor, in order."""
        for p in self:
            p.subtask_instance_started(task, host)

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Call ``subtask_instance_completed`` on every processor, in order."""
        for p in self:
            p.subtask_instance_completed(task, host, result)
