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
    if host is None:
        host = task.host

    try:
        host.host
    except AttributeError:
        msg = "Both Netmiko and Brigade have a host argument. Use the 'netmiko_host' argument " \
              "or the 'ip' argument to specify a device to connect to (if not specifying in " \
              "Brigade's inventory)."
        raise AttributeError(msg)

    parameters = {
        "host": host.host,
        "username": host.username,
        "password": host.password,
        "port": host.ssh_port
    }
    if host.nos is not None:
        # Look device_type up in corresponding map, if no entry return the host.nos unmodified
        device_type = napalm_to_netmiko_map.get(host.nos, host.nos)
        parameters['device_type'] = device_type

    # Both netmiko and brigade use host, allow passing of an alternately named host argument
    if netmiko_args.get("netmiko_host"):
        netmiko_host = netmiko_args.pop("netmiko_host")
        netmiko_args['host'] = netmiko_host

    parameters.update(**netmiko_args)
    host.connections["netmiko"] = ConnectHandler(**parameters)
