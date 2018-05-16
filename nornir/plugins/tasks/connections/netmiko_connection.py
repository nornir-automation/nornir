from netmiko import ConnectHandler

napalm_to_netmiko_map = {
    "ios": "cisco_ios",
    "nxos": "cisco_nxos",
    "eos": "arista_eos",
    "junos": "juniper_junos",
    "iosxr": "cisco_xr",
}


def netmiko_connection(task, **netmiko_args):
    """Connect to the host using Netmiko and set the relevant connection in the connection map.

    Precedence: ``**netmiko_args`` > discrete inventory attributes > inventory netmiko_options

    Arguments:
        ``**netmiko_args``: All supported Netmiko ConnectHandler arguments
    """
    host = task.host
    parameters = {
        "host": host.host,
        "username": host.username,
        "password": host.password,
        "port": host.ssh_port,
    }

    if host.nos is not None:
        # Look device_type up in corresponding map, if no entry return the host.nos unmodified
        device_type = napalm_to_netmiko_map.get(host.nos, host.nos)
        parameters["device_type"] = device_type

    # Precedence order: **netmiko_args > discrete inventory attributes > inventory netmiko_options
    netmiko_connection_args = host.get("netmiko_options", {})
    netmiko_connection_args.update(parameters)
    netmiko_connection_args.update(netmiko_args)
    host.connections["netmiko"] = ConnectHandler(**netmiko_connection_args)
