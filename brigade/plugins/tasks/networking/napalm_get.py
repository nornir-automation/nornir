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

    if not isinstance(getters, list):
        getters = [getters]

    result = {}
    for g in getters:
        if not g.startswith("get_"):
            getter = "get_{}".format(g)
        method = getattr(device, getter)
        result[g] = method()
    return Result(host=task.host, result=result)
