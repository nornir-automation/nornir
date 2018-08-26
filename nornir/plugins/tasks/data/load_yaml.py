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
    with open(file, "r") as f:
        yml = ruamel.yaml.YAML(typ="safe")
        data = yml.load(f)

    return Result(host=task.host, result=data)
