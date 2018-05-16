from nornir.core.task import Result


def napalm_cli(task, commands):
    """
    Run commands on remote devices using napalm

    Arguments:
        commands (``list``): List of commands to execute

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the result of the commands
    """
    device = task.host.get_connection("napalm")
    result = device.cli(commands)
    return Result(host=task.host, result=result)
