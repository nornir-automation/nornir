from typing import Dict

from nornir.core.task import Result, Task

import ruamel.yaml


def load_yaml(task: Task, file: str):
    """
    Loads a yaml file.

    Arguments:
        file: path to the file containing the yaml file to load

    Examples:

        Simple example with ``ordered_dict``::

            > nr.run(task=load_yaml,
                     file="mydata.yaml")

    Returns:
        Result object with the following attributes set:
          * result (``dict``): dictionary with the contents of the file
    """
    kwargs: Dict[str, str] = {}
    with open(file, "r") as f:
        yml = ruamel.yaml.YAML(pure=True, **kwargs)
        data = yml.load(f.read())

    return Result(host=task.host, result=data)
