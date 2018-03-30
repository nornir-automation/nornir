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


def print_result(result, host=None, vars=None, failed=None, task_id=None):
    """
    Prints on screen the :obj:`brigade.core.task.Result` from a previous task

    Arguments:
        result (:obj:`brigade.core.task.Result`): from a previous task
        vars (list of str): Which attributes you want to print
        failed (``bool``): if ``True`` assume the task failed
        task_id (``int``): if we have a :obj:`brigade.core.task.MultiResult` print
            only task in this position

    Returns:
        :obj:`brigade.core.task.Result`:
    """
    #  def print_aggregated_result(host, result):
    #      title = "" if result.changed is None else " ** changed : {} ".format(host_data.changed)
    #      msg = "* {}{}".format(host, title)
    #      print("{}{}{}{}".format(Style.BRIGHT, color, msg, "*" * (80 - len(msg))))

    vars = vars or ["diff", "result", "stdout"]
    if isinstance(vars, str):
        vars = [vars]

    if isinstance(result, AggregatedResult):
        msg = result.name
        print("{}{}{}{}".format(Style.BRIGHT, Fore.CYAN, msg, "*" * (80 - len(msg))))
        for host, host_data in result.items():
            title = "" if host_data.changed is None else \
                    " ** changed : {} ".format(host_data.changed)
            msg = "* {}{}".format(host, title)
            print("{}{}{}{}".format(Style.BRIGHT, Fore.BLUE, msg, "*" * (80 - len(msg))))
            print_result(host_data, host, vars, failed, task_id)
    elif isinstance(result, MultiResult):
        if task_id is not None:
            r = result[task_id]
            result = MultiResult(result.name)
            result.append(r)

        for r in result:
            print_result(r, host, vars, failed, task_id)
        print()
    elif isinstance(result, Result):
        if result.failed or failed:
            color = Fore.RED
        elif result.changed:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN
        subtitle = "" if result.changed is None else " ** changed : {} ".format(result.changed)
        msg = "---- {}{} ".format(result.name, subtitle)
        print("{}{}{}{}".format(Style.BRIGHT, color, msg, "-" * (80 - len(msg))))
        for v in vars:
            x = getattr(result, v, "")
            if x and not isinstance(x, str):
                pprint.pprint(x, indent=2)
            elif x:
                print(x)
