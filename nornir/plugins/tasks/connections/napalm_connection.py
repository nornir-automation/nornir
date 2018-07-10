from napalm import get_network_driver


def napalm_connection(task=None, timeout=60, optional_args=None):
    """
    This tasks connects to the device using the NAPALM driver and sets the
    relevant connection.

    Arguments:
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to `{"port": task.host["nornir_network_api_port"]}`

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

    platform = host.nos
    api_platforms = ["nxos", "eos", "iosxr", "junos"]
    ssh_platforms = ["nxos_ssh", "ios"]

    # If port is set in optional_args that will control the port setting (else look to inventory)
    if "port" not in parameters["optional_args"]:
        if platform in api_platforms and host.network_api_port:
            parameters["optional_args"]["port"] = host.network_api_port
        elif platform in ssh_platforms and host.ssh_port:
            parameters["optional_args"]["port"] = host.ssh_port

        # Setting host.nos to 'nxos' is potentially ambiguous
        if platform == "nxos":
            if not host.network_api_port:
                if host.ssh_port or parameters["optional_args"].get("port") == 22:
                    platform == "nxos_ssh"

        # Fallback for community drivers (priority api_port over ssh_port)
        if platform not in (api_platforms + ssh_platforms):
            if host.network_api_port:
                parameters["optional_args"]["port"] = host.network_api_port
            elif host.ssh_port:
                parameters["optional_args"]["port"] = host.ssh_port

    network_driver = get_network_driver(platform)
    host.connections["napalm"] = network_driver(**parameters)
    host.connections["napalm"].open()
