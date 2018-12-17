from typing import Any, List, Optional

from nornir.core.task import Result, Task


def netmiko_send_config(
    task: Task,
    config_commands: Optional[List[str]] = None,
    config_file: Optional[str] = None,
    **kwargs: Any
) -> Result:
    """
    Execute Netmiko send_config_set method (or send_config_from_file)

    Arguments:
        config_commands: Commands to configure on the remote network device.
        config_file: File to read configuration commands from.
        kwargs: Additional arguments to pass to method.

    Returns:
        Result object with the following attributes set:
          * result (``str``): string showing the CLI from the configuration changes.
    """
    net_connect = task.host.get_connection("netmiko", task.nornir.config)
    net_connect.enable()
    if config_commands:
        result = net_connect.send_config_set(config_commands=config_commands, **kwargs)
    elif config_file:
        result = net_connect.send_config_from_file(config_file=config_file, **kwargs)
    else:
        raise ValueError("Must specify either config_commands or config_file")

    return Result(host=task.host, result=result, changed=True)
