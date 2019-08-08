from typing import List

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

from typing_extensions import Protocol


class Processor(Protocol):
    def task_started(self, task: Task) -> None:
        raise NotImplementedError("needs to be implemented by the processor")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        raise NotImplementedError("needs to be implemented by the processor")

    def host_started(self, task: Task, host: Host) -> None:
        raise NotImplementedError("needs to be implemented by the processor")

    def host_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        raise NotImplementedError("needs to be implemented by the processor")


class Processors(List[Processor]):
    def task_started(self, task: Task) -> None:
        for p in self:
            p.task_started(task)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        for p in self:
            p.task_completed(task, result)

    def host_started(self, task: Task, host: Host) -> None:
        for p in self:
            p.host_started(task, host)

    def host_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        for p in self:
            p.host_completed(task, host, result)
