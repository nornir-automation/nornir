from netmiko import ConnectHandler

napalm_to_netmiko_map = {
    'ios': 'cisco_ios',
    'nxos': 'cisco_nxos',
    'eos': 'arista_eos',
    'junos': 'juniper_junos',
    'iosxr': 'cisco_iosxr'
}


def netmiko_connection(task=None, host=None, **netmiko_args):
    """Connect to the host using Netmiko and set the relevant connection in the connection map.

    Arguments:
        **netmiko_args: All supported Netmiko ConnectHandler arguments
    """
    if netmiko_args is None:
        netmiko_args = {}

    if host is None:
        host = task.host

    parameters = {
        "host": host.host,
        "username": host.username,
        "password": host.password,
        "port": host.ssh_port
    }
    if timeout is not None:
        parameters['timeout'] = timeout
    if host.nos is not None:
        # Try to look it up in map, if it fails just return the host.nos
        device_type = napalm_to_netmiko_map.get(host.nos, host.nos)
        parameters['device_type'] = device_type

    parameters.update(**netmiko_args)
    host.connections["netmiko"] = ConnectHandler(**parameters)
