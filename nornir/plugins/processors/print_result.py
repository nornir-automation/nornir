import logging
import threading
from typing import Union, cast

from colorama import Fore, Style, init

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

init(autoreset=True, strip=False)


def _get_color(result: Union[MultiResult, Result]) -> str:
    if result.failed:
        color = Fore.RED
    elif result.changed:
        color = Fore.YELLOW
    else:
        color = Fore.GREEN
    return cast(str, color)


class PrintResult:
    """
    Prints information about the task execution on screen.

    Arguments:
        severity_level: Print only results with this severity level or higher
    """

    def __init__(self, severity_level: int = logging.INFO) -> None:
        self.severity_level = severity_level
        self.lock = threading.Lock()

    def task_started(self, task: Task) -> None:
        if task.severity_level < self.severity_level:
            return

        msg = f"**** {task.name} - Starting "
        print(f"{Style.BRIGHT}{Fore.CYAN}{msg}{'*' * (80 - len(msg))}")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        if task.severity_level < self.severity_level:
            return

        msg = f"**** {task.name} - Completed "
        print(f"{Style.BRIGHT}{Fore.CYAN}{msg}{'*' * (80 - len(msg))}")

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass

    def task_instance_completed(
        self, task: Task, host: Host, results: MultiResult
    ) -> None:
        self.lock.acquire()
        if task.severity_level < self.severity_level:
            self.lock.release()
            return

        # print task
        msg = f"vvvv {task.name} - {host.name} ** changed: {results.changed} "
        level_name = logging.getLevelName(results.severity_level)
        print(
            f"{Style.BRIGHT}{_get_color(results)}{msg}{'v' * (80 - len(msg))} {level_name}"
        )
        print(results.result)

        # print task footer
        print(f"{Style.BRIGHT}{_get_color(results)}{'^' * 80}")

        self.lock.release()

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self.task_instance_started(task, host)

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        self.task_instance_completed(task, host, result)
