import copy

from nornir.core.task import Result


def napalm_get(task, getters, getters_options=None, **kwargs):
    """
    Gather information from network devices using napalm

    Arguments:
        getters (list of str): getters to use
        getters_options (dict of dicts): When passing multiple getters you
            pass a dictionary where the outer key is the getter name
            and the included dictionary represents the options to pass
            to the getter
        **kwargs: will be passed as they are to the getters

    Examples:

        Simple example::

            > nr.run(task=napalm_get,
            >        getters=["interfaces", "facts"])

        Passing options using ``**kwargs``::

            > nr.run(task=napalm_get,
            >        getters=["config"],
            >        retrieve="all")

        Passing options using ``getters_options``::

            > nr.run(task=napalm_get,
            >        getters=["config", "interfaces"],
            >        getters_options={"config": {"retrieve": "all"}})

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
    """
    device = task.host.get_connection("napalm")
    getters_options = getters_options or {}

    if isinstance(getters, str):
        getters = [getters]

    result = {}
    for g in getters:
        options = copy.deepcopy(kwargs)
        options.update(getters_options.get(g, {}))
        getter = g if g.startswith("get_") else "get_{}".format(g)
        method = getattr(device, getter)
        result[g] = method(**options)
    return Result(host=task.host, result=result)
