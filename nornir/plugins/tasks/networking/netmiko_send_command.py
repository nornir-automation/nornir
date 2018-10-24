from typing import Any

from nornir.core.task import Result, Task


def netmiko_send_command(
    task: Task, command_string: str, use_timing: bool = False, **kwargs: Any
) -> Result:
    """
    Execute Netmiko send_command method (or send_command_timing)

    Arguments:
        command_string: Command to execute on the remote network device.
        use_timing: Set to True to switch to send_command_timing method.
        kwargs: Additional arguments to pass to send_command method.

    Returns:
        Result object with the following attributes set:
          * result (``dict``): dictionary with the result of the show command.
    """
    net_connect = task.host.get_connection("netmiko", task.nornir.config)
    if use_timing:
        result = net_connect.send_command_timing(command_string, **kwargs)
    else:
        result = net_connect.send_command(command_string, **kwargs)
    return Result(host=task.host, result=result)
