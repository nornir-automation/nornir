import collections
import json

from nornir.core.task import Result


def load_json(task, file, ordered_dict=False):
    """
    Loads a json file.

    Arguments:
        file (str): path to the file containing the json file to load
        ordered_dict (bool): If set to true used OrderedDict to load maps

    Examples:

        Simple example with ``ordered_dict``::

            > nr.run(task=load_json,
                     file="mydata.json",
                     ordered_dict=True)

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the contents of the file
    """
    kwargs = {}
    if ordered_dict:
        kwargs["object_pairs_hook"] = collections.OrderedDict
    with open(file, "r") as f:
        data = json.loads(f.read(), **kwargs)

    return Result(host=task.host, result=data)
