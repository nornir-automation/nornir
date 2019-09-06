from typing import Dict

from nornir.core import Nornir
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task


def mock_task(task: Task) -> Result:
    if task.host.hostname == "dev3.group_2":
        raise Exception("failed!!!")
    return Result(host=task.host, result=True)


def mock_subtask(task: Task) -> Result:
    task.run(task=mock_task)
    return Result(host=task.host, result=True)


class MockProcessor:
    def __init__(self, data: Dict[str, None]) -> None:
        self.data = data

    def task_started(self, task: Task) -> None:
        self.data[task.name] = {"started": True}

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.data[task.name]["completed"] = True

    def host_started(self, task: Task, host: Host, is_subtask: bool) -> None:
        if is_subtask and task.name not in self.data:
            self.data[task.name] = {"started": True, "is_subtask": True}
        self.data[task.name][host.hostname] = {"started": True}

    def host_completed(
        self, task: Task, host: Host, results: MultiResult, is_subtask: bool
    ) -> None:
        self.data[task.name][host.hostname] = {
            "completed": True,
            "failed": results.failed,
        }


class Test:
    def test_processor(self, nornir: Nornir) -> None:
        data = {}
        nornir.with_processors([MockProcessor(data)]).run(task=mock_task)
        assert data == {
            "mock_task": {
                "started": True,
                "dev1.group_1": {"completed": True, "failed": False},
                "dev2.group_1": {"completed": True, "failed": False},
                "dev3.group_2": {"completed": True, "failed": True},
                "dev4.group_2": {"completed": True, "failed": False},
                "dev5.no_group": {"completed": True, "failed": False},
                "completed": True,
            }
        }

    def test_processor_subtasks(self, nornir: Nornir) -> None:
        data = {}
        nornir.with_processors([MockProcessor(data)]).run(task=mock_subtask)
        assert data == {
            "mock_subtask": {
                "started": True,
                "dev1.group_1": {"completed": True, "failed": False},
                "dev2.group_1": {"completed": True, "failed": False},
                "dev3.group_2": {"completed": True, "failed": True},
                "dev4.group_2": {"completed": True, "failed": False},
                "dev5.no_group": {"completed": True, "failed": False},
                "completed": True,
            },
            "mock_task": {
                "started": True,
                "is_subtask": True,
                "dev1.group_1": {"completed": True, "failed": False},
                "dev2.group_1": {"completed": True, "failed": False},
                "dev3.group_2": {"completed": True, "failed": True},
                "dev4.group_2": {"completed": True, "failed": False},
                "dev5.no_group": {"completed": True, "failed": False},
            },
        }
