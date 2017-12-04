from brigade.core.task import Result

from netmiko import ConnectHandler

napalm_to_netmiko_map = {
    'ios': 'cisco_ios',
    'nxos': 'cisco_nxos',
    'eos': 'arista_eos',
    'junos': 'juniper_junos',
    'iosxr': 'cisco_iosxr'
}


def netmiko_run(task, method, netmiko_dict=None, **kwargs):
    """
    Execute any Netmiko method from connection class (BaseConnection class and children).

    Arguments:
        method(str): Netmiko method to use
        netmiko_dict (dict, optional): Additional arguments to pass to Netmiko ConnectHandler, \
        defaults to None

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
    """
    parameters = {
        "ip": task.host.host,
        "username": task.host.username,
        "password": task.host.password,
        "port": task.host.ssh_port,
    }
    parameters.update(netmiko_dict or {})
    device_type = task.host.nos
    # Convert to netmiko device_type format (if napalm format is used)
    parameters['device_type'] = napalm_to_netmiko_map.get(device_type, device_type)

    with ConnectHandler(**parameters) as net_connect:
        netmiko_method = getattr(net_connect, method)
        result = netmiko_method(**kwargs)
    return Result(host=task.host, result=result)
