import pprint

from brigade.core.task import AggregatedResult, MultiResult, Result

from colorama import Fore, Style, init


init(autoreset=True, convert=False, strip=False)


def print_result(task, data, vars=None, failed=None, task_id=None):
    """
    Prints on screen the :obj:`brigade.core.task.Result` from a previous task

    Arguments:
        data (:obj:`brigade.core.task.Result`): from a previous task
        vars (list of str): Which attributes you want to print
        failed (``bool``): if ``True`` assume the task failed
        task_id (``int``): if we have a :obj:`brigade.core.task.MultiResult` print
            only task in this position

    Returns:
        :obj:`brigade.core.task.Result`:
    """
    vars = vars or ["diff", "result", "stdout"]
    if isinstance(vars, str):
        vars = [vars]

    if isinstance(data, AggregatedResult):
        data = data[task.host.name]

    if task_id is not None:
        r = data[task_id]
        data = MultiResult(data.name)
        data.append(r)

    if data.failed or failed:
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
            if x and not isinstance(x, str):
                pprint.pprint(x, indent=2)
            elif x:
                print(x)
    print()

    return Result(task.host)
