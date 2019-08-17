from typing import Dict

from nornir.core import Nornir
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task


def mock_task(task: Task) -> Result:
    if task.host.hostname == "dev3.group_2":
        raise Exception("failed!!!")
    return Result(host=task.host, result=True)


class MockProcessor:
    def __init__(self, data: Dict[str, None]) -> None:
        self.data = data

    def task_started(self, task: Task) -> None:
        self.data[task.name] = {}
        self.data[task.name]["started"] = True

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.data[task.name]["completed"] = True

    def host_started(self, task: Task, host: Host) -> None:
        self.data[task.name][host.hostname] = {"started": True}

    def host_completed(self, task: Task, host: Host, results: MultiResult) -> None:
        self.data[task.name][host.hostname] = {
            "completed": True,
            "result": results.result,
        }


class Test:
    def test_processor(self, nornir: Nornir) -> None:
        data = {}
        nornir.with_processors([MockProcessor(data)]).run(task=mock_task)
        print(data)
        assert data == {
            "mock_task": {
                "started": True,
                "dev1.group_1": {"completed": True, "result": True},
                "dev2.group_1": {"completed": True, "result": True},
                "dev3.group_2": {
                    "completed": True,
                    "result": 'Traceback (most recent call last):\n  File "/nornir/nornir/core/task.py", line 77, in start\n    r = self.task(self, **self.params)\n  File "/nornir/tests/core/test_processors.py", line 10, in mock_task\n    raise Exception("failed!!!")\nException: failed!!!\n',  # noqa
                },
                "dev4.group_2": {"completed": True, "result": True},
                "dev5.no_group": {"completed": True, "result": True},
                "completed": True,
            }
        }
