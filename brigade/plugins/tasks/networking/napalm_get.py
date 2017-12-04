from brigade.core.task import Result

from napalm import get_network_driver


def napalm_get(task, getters, timeout=60, optional_args=None):
    """
    Gather information from network devices using napalm

    Arguments:
        getters (list of str): getters to use
        hostname (string, optional): defaults to ``brigade_ip``
        username (string, optional): defaults to ``brigade_username``
        password (string, optional): defaults to ``brigade_password``
        driver (string, optional): defaults to ``nos``
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["napalm_port"]}``


    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
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

    if not isinstance(getters, list):
        getters = [getters]

    with network_driver(**parameters) as device:
        result = {}
        for g in getters:
            if not g.startswith("get_"):
                getter = "get_{}".format(g)
            method = getattr(device, getter)
            result[g] = method()
    return Result(host=task.host, result=result)
