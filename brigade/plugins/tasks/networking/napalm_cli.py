from brigade.core.task import Result

from napalm import get_network_driver


def napalm_cli(task, commands, timeout=60, optional_args=None):
    """
    Run commands on remote devices using napalm

    Arguments:
        commands (list): list of commands to execute on the device
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["napalm_port"]}``


    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the result of the commands
    """
    parameters = {
        "hostname": task.host.host,
        "username": task.host.username,
        "password": task.host.password,
        "timeout": timeout,
        "optional_args": optional_args or {},
    }
    if "port" not in parameters["optional_args"] and task.host.network_api_port:
        parameters["optional_args"]["port"] = task.host.network_api_port
    network_driver = get_network_driver(task.host.nos)

    with network_driver(**parameters) as device:
        result = device.cli(commands)
    return Result(host=task.host, result=result)
