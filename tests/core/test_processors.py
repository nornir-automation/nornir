from typing import Any, Dict

from nornir.core import Nornir
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task


def mock_task(task: Task) -> Result:
    if task.host.hostname == "dev3.group_2":
        raise Exception("failed!!!")
    return Result(host=task.host, result=True)


def mock_subsubtask(task: Task) -> Result:
    task.run(task=mock_task)
    return Result(host=task.host, result=True)


def mock_subtask(task: Task) -> Result:
    task.run(task=mock_task)
    task.run(task=mock_subsubtask)
    return Result(host=task.host, result=True)


class MockProcessor:
    def __init__(self, data: Dict[str, None]) -> None:
        self.data = data

    def task_started(self, task: Task) -> None:
        self.data[task.name] = {"started": True}

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.data[task.name]["completed"] = True

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.data[task.name][host.hostname] = {"started": True, "subtasks": {}}

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        self.data[task.name][host.hostname]["completed"] = True
        self.data[task.name][host.hostname]["failed"] = result.failed

    def _get_subtask_dict(self, task: Task, host: Host) -> Dict[str, Any]:
        parents = []
        parent = task.parent_task
        while True:
            if parent is None:
                break
            parents.insert(0, parent.name)
            parent = parent.parent_task

        data = self.data[parents[0]][host.hostname]["subtasks"]
        for p in parents[1:]:
            data = data[p]["subtasks"]
        return data

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        data = self._get_subtask_dict(task, host)
        data[task.name] = {"started": True, "subtasks": {}}

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        data = self._get_subtask_dict(task, host)
        data[task.name]["completed"] = True
        data[task.name]["failed"] = result.failed


class Test:
    def test_processor(self, nornir: Nornir) -> None:
        data = {}
        nornir.with_processors([MockProcessor(data)]).run(task=mock_task)
        assert data == {
            "mock_task": {
                "started": True,
                "dev1.group_1": {
                    "started": True,
                    "subtasks": {},
                    "completed": True,
                    "failed": False,
                },
                "dev2.group_1": {
                    "started": True,
                    "subtasks": {},
                    "completed": True,
                    "failed": False,
                },
                "dev3.group_2": {
                    "started": True,
                    "subtasks": {},
                    "completed": True,
                    "failed": True,
                },
                "dev4.group_2": {
                    "started": True,
                    "subtasks": {},
                    "completed": True,
                    "failed": False,
                },
                "dev5.no_group": {
                    "started": True,
                    "subtasks": {},
                    "completed": True,
                    "failed": False,
                },
                "completed": True,
            }
        }

    def test_processor_subtasks(self, nornir: Nornir) -> None:
        data = {}
        nornir.with_processors([MockProcessor(data)]).run(task=mock_subtask)
        assert data == {
            "mock_subtask": {
                "started": True,
                "dev1.group_1": {
                    "started": True,
                    "subtasks": {
                        "mock_task": {
                            "started": True,
                            "subtasks": {},
                            "completed": True,
                            "failed": False,
                        },
                        "mock_subsubtask": {
                            "started": True,
                            "subtasks": {
                                "mock_task": {
                                    "started": True,
                                    "subtasks": {},
                                    "completed": True,
                                    "failed": False,
                                }
                            },
                            "completed": True,
                            "failed": False,
                        },
                    },
                    "completed": True,
                    "failed": False,
                },
                "dev2.group_1": {
                    "started": True,
                    "subtasks": {
                        "mock_task": {
                            "started": True,
                            "subtasks": {},
                            "completed": True,
                            "failed": False,
                        },
                        "mock_subsubtask": {
                            "started": True,
                            "subtasks": {
                                "mock_task": {
                                    "started": True,
                                    "subtasks": {},
                                    "completed": True,
                                    "failed": False,
                                }
                            },
                            "completed": True,
                            "failed": False,
                        },
                    },
                    "completed": True,
                    "failed": False,
                },
                "dev3.group_2": {
                    "started": True,
                    "subtasks": {
                        "mock_task": {
                            "started": True,
                            "subtasks": {},
                            "completed": True,
                            "failed": True,
                        }
                    },
                    "completed": True,
                    "failed": True,
                },
                "dev4.group_2": {
                    "started": True,
                    "subtasks": {
                        "mock_task": {
                            "started": True,
                            "subtasks": {},
                            "completed": True,
                            "failed": False,
                        },
                        "mock_subsubtask": {
                            "started": True,
                            "subtasks": {
                                "mock_task": {
                                    "started": True,
                                    "subtasks": {},
                                    "completed": True,
                                    "failed": False,
                                }
                            },
                            "completed": True,
                            "failed": False,
                        },
                    },
                    "completed": True,
                    "failed": False,
                },
                "dev5.no_group": {
                    "started": True,
                    "subtasks": {
                        "mock_task": {
                            "started": True,
                            "subtasks": {},
                            "completed": True,
                            "failed": False,
                        },
                        "mock_subsubtask": {
                            "started": True,
                            "subtasks": {
                                "mock_task": {
                                    "started": True,
                                    "subtasks": {},
                                    "completed": True,
                                    "failed": False,
                                }
                            },
                            "completed": True,
                            "failed": False,
                        },
                    },
                    "completed": True,
                    "failed": False,
                },
                "completed": True,
            }
        }
