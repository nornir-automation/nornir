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
