from brigade.core.task import Result


def napalm_get(task, getters):
    """
    Gather information from network devices using napalm

    Arguments:
        getters (list of str): getters to use


    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
    """
    device = task.host.get_connection("napalm")

    if isinstance(getters, str):
        getters = [getters]

    result = {}
    for g in getters:
        if not g.startswith("get_"):
            g = "get_{}".format(g)
        method = getattr(device, g)
        result[g] = method()
    return Result(host=task.host, result=result)
