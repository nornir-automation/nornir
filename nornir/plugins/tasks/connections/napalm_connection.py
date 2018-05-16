from napalm import get_network_driver


def napalm_connection(task=None, timeout=60, optional_args=None):
    """
    This tasks connects to the device using the NAPALM driver and sets the
    relevant connection.

    Arguments:
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["network_api_port"]}``

    Inventory:
        napalm_options: maps directly to ``optional_args`` when establishing the connection
        network_api_port: maps to ``optional_args["port"]``
    """
    host = task.host

    parameters = {
        "hostname": host.host,
        "username": host.username,
        "password": host.password,
        "timeout": timeout,
        "optional_args": optional_args or host.get("napalm_options", {}),
    }
    if "port" not in parameters["optional_args"] and host.network_api_port:
        parameters["optional_args"]["port"] = host.network_api_port
    elif "port" not in parameters["optional_args"] and host.ssh_port:
        parameters["optional_args"]["port"] = host.ssh_port
    network_driver = get_network_driver(host.nos)

    host.connections["napalm"] = network_driver(**parameters)
    host.connections["napalm"].open()
