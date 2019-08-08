import logging

from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir.plugins.functions.text import print_result
from nornir.plugins.processors.print_result import PrintResult

nr = InitNornir(
    #  core={"num_workers": 1},
    inventory={
        "options": {
            "hosts": {
                "rtr00": {
                    "hostname": "localhost",
                    "username": "admin",
                    "password": "admin",
                    "platform": "ios",
                    "connection_options": {
                        "napalm": {
                            "platform": "mock",
                            "extras": {"optional_args": {"path": "mocked/rtr00/"}},
                        }
                    },
                },
                "rtr01": {
                    "hostname": "localhost",
                    "username": "admin",
                    "password": "admin",
                    "platform": "junos",
                    "connection_options": {
                        "napalm": {
                            "platform": "mock",
                            "extras": {"optional_args": {"path": "mocked/rtr01/"}},
                        }
                    },
                },
            }
        }
    }
)


def subtask(task: Task, msg: str) -> Result:
    if msg == "task2":
        raise Exception("shit!")
    return Result(host=task.host, result=msg)


def test_task(task: Task) -> Result:
    task.run(task=subtask, msg="task1")
    task.run(task=subtask, msg="task2", severity_level=logging.DEBUG)
    return Result(host=task.host, result="dummy result")


nr.with_processors([PrintResult()]).run(task=test_task)
