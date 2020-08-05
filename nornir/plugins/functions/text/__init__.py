import logging
import pprint
import threading
from typing import List, Optional, cast
from collections import OrderedDict
import json
import sys
from io import StringIO
from colorama import Fore, Style, init
from typing import Union, TextIO
from nornir.core.task import AggregatedResult, MultiResult, Result


LOCK = threading.Lock()

init(autoreset=True, strip=False)


def print_title(title: str) -> None:
    """
    Helper function to print a title.
    """
    msg = "**** {} ".format(title)
    print("{}{}{}{}".format(Style.BRIGHT, Fore.GREEN, msg, "*" * (80 - len(msg))))


def _get_color(result: Result, failed: bool) -> str:
    if result.failed or failed:
        color = Fore.RED
    elif result.changed:
        color = Fore.YELLOW
    else:
        color = Fore.GREEN
    return cast(str, color)


def _print_individual_result(
    result: Result,
    host: Optional[str],
    attrs: List[str],
    failed: bool,
    severity_level: int,
    dest: Union[StringIO, TextIO],
    task_group: bool = False,
) -> None:

    out_buffer = dest

    if result.severity_level < severity_level:
        return

    color = _get_color(result, failed)
    subtitle = (
        "" if result.changed is None else " ** changed : {} ".format(result.changed)
    )
    level_name = logging.getLevelName(result.severity_level)
    symbol = "v" if task_group else "-"
    msg = "{} {}{}".format(symbol * 4, result.name, subtitle)
    print(
        "{}{}{}{} {}".format(
            Style.BRIGHT, color, msg, symbol * (80 - len(msg)), level_name
        ),
        file=out_buffer,
    )
    for attribute in attrs:
        x = getattr(result, attribute, "")
        if isinstance(x, BaseException):
            # for consistency between py3.6 and py3.7
            print(f"{x.__class__.__name__}{x.args}", file=out_buffer)
        elif x and not isinstance(x, str):
            if isinstance(x, OrderedDict):
                print(json.dumps(x, indent=2), file=out_buffer)
            else:
                pprint.pprint(x, indent=2, stream=out_buffer)
        elif x:
            print(x, file=out_buffer)


def _print_result(
    result: Result,
    host: Optional[str] = None,
    attrs: List[str] = None,
    failed: bool = False,
    dest: Union[TextIO, StringIO, None] = None,
    severity_level: int = logging.INFO,
) -> None:

    out_buffer = sys.stdout if dest is None else dest

    attrs = attrs or ["diff", "result", "stdout"]
    if isinstance(attrs, str):
        attrs = [attrs]

    if isinstance(result, AggregatedResult):
        msg = result.name
        print(
            "{}{}{}{}".format(Style.BRIGHT, Fore.CYAN, msg, "*" * (80 - len(msg))),
            file=out_buffer,
        )
        for host, host_data in sorted(result.items()):
            title = (
                ""
                if host_data.changed is None
                else " ** changed : {} ".format(host_data.changed)
            )
            msg = "* {}{}".format(host, title)
            print(
                "{}{}{}{}".format(Style.BRIGHT, Fore.BLUE, msg, "*" * (80 - len(msg))),
                file=out_buffer,
            )
            _print_result(
                host_data, host, attrs, failed, out_buffer, severity_level,
            )
    elif isinstance(result, MultiResult):
        _print_individual_result(
            result[0], host, attrs, failed, severity_level, out_buffer, task_group=True,
        )
        for r in result[1:]:
            _print_result(
                r, host, attrs, failed, out_buffer, severity_level,
            )
        color = _get_color(result[0], failed)
        msg = "^^^^ END {} ".format(result[0].name)
        print(
            "{}{}{}{}".format(Style.BRIGHT, color, msg, "^" * (80 - len(msg))),
            file=out_buffer,
        )
    elif isinstance(result, Result):
        _print_individual_result(
            result, host, attrs, failed, severity_level, out_buffer
        )


def print_result(
    result: Result,
    host: Optional[str] = None,
    vars: List[str] = None,
    failed: bool = False,
    severity_level: int = logging.INFO,
    dest: Optional[StringIO] = None,
) -> None:
    """
    Prints the :obj:`nornir.core.task.Result` from a previous task to screen

    Arguments:
        result: from a previous task
        host: # TODO
        vars: Which attributes you want to print
        failed: if ``True`` assume the task failed
        severity_level: Print only errors with this severity level or higher
        dest: default=None, String buffer to write output into.
    """
    LOCK.acquire()
    try:
        _print_result(result, host, vars, failed, dest, severity_level)
    finally:
        LOCK.release()
