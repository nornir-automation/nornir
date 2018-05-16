from nornir.core.task import Result


def napalm_get(task, getters):
    """
    Gather information from network devices using napalm

    Arguments:
        getters (list of str): getters to use


    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
    """
    device = task.host.get_connection("napalm")

    if isinstance(getters, str):
        getters = [getters]

    result = {}
    for g in getters:
        getter = g if g.startswith("get_") else "get_{}".format(g)
        method = getattr(device, getter)
        result[g] = method()
    return Result(host=task.host, result=result)
