from napalm import get_network_driver


def napalm_connection(task=None, host=None, timeout=60, optional_args=None):
    """
    This tasks connects to the device using the NAPALM driver and sets the
    relevant connection.

    Arguments:
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["napalm_port"]}``

    Inventory:
        napalm_options: maps directly to ``optional_args`` when establishing the connection
        network_api_port: maps to ``optional_args["port"]``
    """
    if host is None:
        host = task.host

    parameters = {
        "hostname": task.host.host,
        "username": task.host.username,
        "password": task.host.password,
        "timeout": timeout,
        "optional_args": optional_args or host.get("napalm_options", {}),
    }
    if "port" not in parameters["optional_args"] and task.host.network_api_port:
        parameters["optional_args"]["port"] = task.host.network_api_port
    network_driver = get_network_driver(task.host.nos)

    host.connections["napalm"] = network_driver(**parameters)
    host.connections["napalm"].open()
