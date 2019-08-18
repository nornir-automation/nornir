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
        msg = f"**** {task.name} "
        print(f"{Style.BRIGHT}{Fore.CYAN}{msg}{'*' * (80 - len(msg))}")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass

    def host_started(self, task: Task, host: Host) -> None:
        pass

    def host_completed(self, task: Task, host: Host, results: MultiResult) -> None:
        self.lock.acquire()

        if results.severity_level < self.severity_level:
            return

        # print host header
        msg = f"* {host.name} ** changed: {results.changed} "
        print(f"{Style.BRIGHT}{Fore.BLUE}{msg}{'*' * (80 - len(msg))}")

        # print task
        msg = f"vvvv {results.name} ** changed: {results.changed} "
        level_name = logging.getLevelName(results.severity_level)
        print(
            f"{Style.BRIGHT}{_get_color(results)}{msg}{'v' * (80 - len(msg))} {level_name}"
        )
        print(results.result)

        # print subtasks
        for result in results[1:]:
            if result.severity_level < self.severity_level:
                continue
            msg = f"--- {result.name} ** changed: {result.changed} "
            print(
                f"{Style.BRIGHT}{_get_color(result)}{msg}{'-' * (80 - len(msg))} {level_name}"
            )
            print(result.result)

        # print task footer
        msg = f"^^^^ END {task.name}"
        print(
            f"{Style.BRIGHT}{_get_color(results)}{msg}{'^' * (80 - len(msg))} {level_name}"
        )

        self.lock.release()
