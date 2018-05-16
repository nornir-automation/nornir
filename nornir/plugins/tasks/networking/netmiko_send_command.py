from nornir.core.task import Result


def netmiko_send_command(task, command_string, use_timing=False, **kwargs):
    """
    Execute Netmiko send_command method (or send_command_timing)

    Arguments:
        command_string(str): Command to execute on the remote network device.
        use_timing(bool, optional): Set to True to switch to send_command_timing method.
        kwargs (dict, optional): Additional arguments to pass to send_command method.

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the result of the show command.
    """
    net_connect = task.host.get_connection("netmiko")
    if use_timing:
        result = net_connect.send_command_timing(command_string, **kwargs)
    else:
        result = net_connect.send_command(command_string, **kwargs)
    return Result(host=task.host, result=result)
