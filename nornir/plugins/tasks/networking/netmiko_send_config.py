from __future__ import unicode_literals

from nornir.core.task import Result


def netmiko_send_config(task, config_commands=None, config_file=None, **kwargs):
    """
    Execute Netmiko send_config_set method (or send_config_from_file)
    Arguments:
        config_commands(list, optional): Commands to configure on the remote network device.
        config_file(str, optional): File to read configuration commands from.
        kwargs (dict, optional): Additional arguments to pass to method.

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary showing the CLI from the configuration changes.
    """
    net_connect = task.host.get_connection("netmiko")
    if config_commands:
        result = net_connect.send_config_set(config_commands=config_commands, **kwargs)
    elif config_file:
        result = net_connect.send_config_from_file(config_file=config_file, **kwargs)
    else:
        raise ValueError("Must specify either config_commands or config_file")

    return Result(host=task.host, result=result, changed=True)
