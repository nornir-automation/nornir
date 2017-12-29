import pprint

from brigade.core.task import AggregatedResult, Result

from colorama import Fore, Style, init


init(autoreset=True)


def print_result(task, data, vars=None):
    """
    Prints on screen the :obj:`brigade.core.task.Result` from a previous task

    Arguments:
        data (:obj:`brigade.core.task.Result`): from a previous task
        vars (list of str): Which attributes you want to print

    Returns:
        :obj:`brigade.core.task.Result`:
    """
    vars = vars or ["diff", "result", "stdout"]
    if isinstance(vars, str):
        vars = [vars]

    if isinstance(data, AggregatedResult):
        data = data[task.host.name]

    if data.failed:
        color = Fore.RED
    elif data.changed:
        color = Fore.YELLOW
    else:
        color = Fore.BLUE
    changed = "" if data.changed is None else " ** changed : {} ".format(data.changed)
    msg = "* {}{}".format(task.host.name, changed)
    print("{}{}{}{}".format(Style.BRIGHT, color, msg, "*" * (80 - len(msg))))
    for v in vars:
        r = getattr(data, v, "")
        if r and not isinstance(r, str):
            pprint.pprint(r)
        elif r:
            print(r)

    return Result(task.host)
