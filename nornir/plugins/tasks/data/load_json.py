import collections
import json
from typing import Dict, MutableMapping, Any, Type

from nornir.core.task import Result, Task


def load_json(task: Task, file: str, ordered_dict: bool = False) -> Result:
    """
    Loads a json file.

    Arguments:
        file: path to the file containing the json file to load
        ordered_dict: If set to true used OrderedDict to load maps

    Examples:

        Simple example with ``ordered_dict``::

            > nr.run(task=load_json,
                     file="mydata.json",
                     ordered_dict=True)
        file: path to the file containing the json file to load

    Returns:
        Result object with the following attributes set:
          * result (``dict``): dictionary with the contents of the file
    """
    kwargs: Dict[str, Type[MutableMapping[str, Any]]] = {}
    if ordered_dict:
        kwargs["object_pairs_hook"] = collections.OrderedDict
    with open(file, "r") as f:
        data = json.loads(f.read(), **kwargs)

    return Result(host=task.host, result=data)
