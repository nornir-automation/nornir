from brigade.core.task import Result

from napalm import get_network_driver


def napalm_configure(task, configuration, replace=False, timeout=60, optional_args=None):
    """
    Loads configuration into a network devices using napalm

    Arguments:
        configuration (str): configuration to load into the device
        replace (bool): whether to replace or merge the configuration
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["napalm_port"]}``


    Returns:
        :obj:`brigade.core.task.Result`:
          * changed (``bool``): whether if the task is changing the system or not
          * diff (``string``): change in the system
    """
    parameters = {
        "hostname": task.host.host,
        "username": task.host.username,
        "password": task.host.password,
        "timeout": timeout,
        "optional_args": optional_args or {},
    }
    if "port" not in parameters["optional_args"] and task.host.network_api_port:
        parameters["optional_args"]["port"] = task.host.network_api_port
    network_driver = get_network_driver(task.host.nos)

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
    return Result(host=task.host, diff=diff, changed=len(diff) > 0)
