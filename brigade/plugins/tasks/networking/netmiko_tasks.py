from brigade.core.task import Result
from netmiko import ConnectHandler
from napalm.base.utils import py23_compat

napalm_to_netmiko_map = {
    'ios': 'cisco_ios',
    'nxos': 'cisco_nxos',
    'eos': 'arista_eos',
    'junos': 'juniper_junos',
    'iosxr': 'cisco_iosxr'
}


def netmiko_args(task, ip=None, host=None, username=None, password=None, device_type=None,
                 netmiko_dict=None):
    """Process arguments coming from different sources."""
    parameters = {
        "username": username or task.host["brigade_username"],
        "password": password or task.host["brigade_password"],
    }

    if host is None and ip is None:
        parameters["ip"] = task.host["brigade_ip"]
    elif ip is not None:
        parameters["ip"] = ip
    elif host is not None:
        parameters["host"] = host

    if netmiko_dict is not None:
        parameters.update(netmiko_dict)
    else:
        netmiko_dict = {}

    if device_type is None:
        if netmiko_dict.get("device_type") is None:
            device_type = task.host["nos"]
        else:
            device_type = netmiko_dict.get("device_type")

    # Convert to netmiko device_type format (if napalm format is used)
    parameters['device_type'] = napalm_to_netmiko_map.get(device_type, device_type)
    return parameters


def netmiko_run(task, method, ip=None, host=None, username=None, password=None,
                device_type=None, netmiko_dict=None, cmd_args=None, cmd_kwargs=None):
    """
    Execute any Netmiko method from connection class (BaseConnection class and children).

    Arguments:
        method(str): Netmiko method to use
        ip (string, optional): defaults to ``brigade_ip``
        host (string, optional): defaults to None
        username (string, optional): defaults to ``brigade_username``
        password (string, optional): defaults to ``brigade_password``
        device_type (string, optional): Netmiko device_type to use, defaults to ``nos`` (mapped \
        through napalm_to_netmiko_map)
        netmiko_dict (dict, optional): Additional arguments to pass to Netmiko ConnectHandler, \
        defaults to None

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
    """
    parameters = netmiko_args(task=task, ip=ip, host=host, username=username,
                              password=password, device_type=device_type, 
                              netmiko_dict=netmiko_dict)
    with ConnectHandler(**parameters) as net_connect:
        netmiko_method = getattr(net_connect, method)
        if cmd_args is None:
            cmd_args = ()
        if cmd_kwargs is None:
            cmd_kwargs = {}
        result = netmiko_method(*cmd_args, **cmd_kwargs)
    return Result(host=task.host, result=result)


def netmiko_send_command(task, ip=None, host=None, username=None, password=None,
                         device_type=None, netmiko_dict=None, cmd_args=None, cmd_kwargs=None):
    parameters = netmiko_args(task=task, ip=ip, host=host, username=username,
                              password=password, device_type=device_type, 
                              netmiko_dict=netmiko_dict)
    with ConnectHandler(**parameters) as net_connect:
        if cmd_args is None:
            cmd_args = ()
        elif isinstance(cmd_args, py23_compat.string_types):
            cmd_args = (cmd_args,)

        if cmd_kwargs is None:
            cmd_kwargs = {}
        result = net_connect.send_command(*cmd_args, **cmd_kwargs)
    return Result(host=task.host, result=result)
