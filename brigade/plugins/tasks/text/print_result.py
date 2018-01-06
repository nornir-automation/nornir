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
    title = "" if data.changed is None else " ** changed : {} ".format(data.changed)
    msg = "* {}{}".format(task.host.name, title)
    print("{}{}{}{}".format(Style.BRIGHT, color, msg, "*" * (80 - len(msg))))
    for r in data:
        subtitle = "" if r.changed is None else " ** changed : {} ".format(r.changed)
        msg = "---- {}{} ".format(r.name, subtitle)
        print("{}{}{}{}".format(Style.BRIGHT, Fore.CYAN, msg, "-" * (80 - len(msg))))
        for v in vars:
            x = getattr(r, v, "")
            if r and not isinstance(x, str):
                pprint.pprint(x)
            elif r:
                print(x)

    return Result(task.host)
