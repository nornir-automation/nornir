from napalm import get_network_driver


def napalm_configure(task, configuration, replace=False, hostname=None, username=None,
                     password=None, driver=None, timeout=60, optional_args=None):
    """
    Loads configuration into a network devices using napalm

    Arguments:
        configuration (str): configuration to load into the device
        replace (bool): whether to replace or merge the configuration
        hostname (string, optional): defaults to ``brigade_ip``
        username (string, optional): defaults to ``brigade_username``
        password (string, optional): defaults to ``brigade_password``
        driver (string, optional): defaults to ``nos``
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["napalm_port"]}``


    Returns:
        dictionary:
          * changed (``bool``): whether if the task is changing the system or not
          * diff (``string``): change in the system
    """
    parameters = {
        "hostname": hostname or task.host["brigade_ip"],
        "username": username or task.host["brigade_username"],
        "password": password or task.host["brigade_password"],
        "timeout": timeout,
        "optional_args": optional_args or {"port": task.host["napalm_port"]},
    }
    network_driver = get_network_driver(driver or task.host["nos"])

    with network_driver(**parameters) as device:
        if replace:
            device.load_replace_candidate(config=configuration)
        else:
            device.load_merge_candidate(config=configuration)
        diff = device.compare_config()

        if task.dry_run:
            device.discard_config()
        else:
            device.commit_config()

    return {
        "changed": len(diff) > 0,
        "diff": diff
    }
