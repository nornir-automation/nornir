import ruamel.yaml
from typing import Dict

from nornir.core.task import Result, Task


def load_yaml(task: Task, file: str, ordered_dict: bool = False):
    """
    Loads a yaml file.

    Arguments:
        file: path to the file containing the yaml file to load
        ordered_dict: If set to true used OrderedDict to load maps

    Examples:

        Simple example with ``ordered_dict``::

            > nr.run(task=load_yaml,
                     file="mydata.yaml",
                     ordered_dict=True)

    Returns:
        Result object with the following attributes set:
          * result (``dict``): dictionary with the contents of the file
    """
    kwargs: Dict[str, str] = {}
    kwargs["typ"] = "rt" if ordered_dict else "safe"
    with open(file, "r") as f:
        yml = ruamel.yaml.YAML(pure=True, **kwargs)
        data = yml.load(f.read())

    return Result(host=task.host, result=data)
