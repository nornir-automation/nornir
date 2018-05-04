import logging
import pprint

from brigade.core.task import AggregatedResult, MultiResult, Result

from colorama import Fore, Style, init


init(autoreset=True, convert=False, strip=False)


def print_title(title):
    """
    Helper function to print a title.
    """
    msg = "**** {} ".format(title)
    print("{}{}{}{}".format(Style.BRIGHT, Fore.GREEN, msg, "*" * (80 - len(msg))))


def _get_color(result, failed):
    if result.failed or failed:
        color = Fore.RED
    elif result.changed:
        color = Fore.YELLOW
    else:
        color = Fore.GREEN
    return color


def _print_individual_result(
    result, host, vars, failed, severity_level, task_group=False
):
    if result.severity_level < severity_level:
        return

    color = _get_color(result, failed)
    subtitle = "" if result.changed is None else " ** changed : {} ".format(
        result.changed
    )
    level_name = logging.getLevelName(result.severity_level)
    symbol = "v" if task_group else "-"
    msg = "{} {}{}".format(symbol * 4, result.name, subtitle)
    print(
        "{}{}{}{} {}".format(
            Style.BRIGHT, color, msg, symbol * (80 - len(msg)), level_name
        )
    )
    for v in vars:
        x = getattr(result, v, "")
        if x and not isinstance(x, str):
            pprint.pprint(x, indent=2)
        elif x:
            print(x)


def print_result(
    result, host=None, vars=None, failed=None, severity_level=logging.INFO
):
    """
    Prints the :obj:`brigade.core.task.Result` from a previous task to screen

    Arguments:
        result (:obj:`brigade.core.task.Result`): from a previous task
        vars (list of str): Which attributes you want to print
        failed (``bool``): if ``True`` assume the task failed
        severity_level (int): Print only errors with this severity level or higher

    Returns:
        :obj:`brigade.core.task.Result`:
    """

    vars = vars or ["diff", "result", "stdout"]
    if isinstance(vars, str):
        vars = [vars]

    if isinstance(result, AggregatedResult):
        msg = result.name
        print("{}{}{}{}".format(Style.BRIGHT, Fore.CYAN, msg, "*" * (80 - len(msg))))
        for host, host_data in sorted(result.items()):
            title = "" if host_data.changed is None else " ** changed : {} ".format(
                host_data.changed
            )
            msg = "* {}{}".format(host, title)
            print(
                "{}{}{}{}".format(Style.BRIGHT, Fore.BLUE, msg, "*" * (80 - len(msg)))
            )
            print_result(host_data, host, vars, failed, severity_level)
    elif isinstance(result, MultiResult):
        _print_individual_result(
            result[0], host, vars, failed, severity_level, task_group=True
        )
        for r in result[1:]:
            print_result(r, host, vars, failed, severity_level)
        color = _get_color(result[0], failed)
        msg = "^^^^ END {} ".format(result[0].name)
        print("{}{}{}{}".format(Style.BRIGHT, color, msg, "^" * (80 - len(msg))))
    elif isinstance(result, Result):
        _print_individual_result(result, host, vars, failed, severity_level)
