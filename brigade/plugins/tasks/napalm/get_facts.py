from napalm import get_network_driver


def napalm_get_facts(task, facts, hostname=None, username=None, password=None,
                     driver=None, timeout=60, optional_args=None):
    """
    Gather facts from a network devices using napalm

    Arguments:
        facts (str): getter to use
        hostname (string, optional): defaults to ``brigade_ip``
        username (string, optional): defaults to ``brigade_username``
        password (string, optional): defaults to ``brigade_password``
        driver (string, optional): defaults to ``nos``
        timeout (int, optional): defaults to 60
        optional_args (dict, optional): defaults to ``{"port": task.host["napalm_port"]}``


    Returns:
        dictionary:
          * result (``dict``): dictionary with the result of the getter
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
        if not facts.startswith("get_"):
            facts = "get_{}".format(facts)
        method = getattr(device, facts)
        result = method()

    return {
        "result": result
    }
