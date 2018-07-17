from nornir.core.task import Result

import ruamel.yaml


def load_yaml(task, file, ordered_dict=False):
    """
    Loads a yaml file.

    Arguments:
        file (str): path to the file containing the yaml file to load
        ordered_dict (bool): If set to true used OrderedDict to load maps

    Examples:

        Simple example with ``ordered_dict``::

            > nr.run(task=load_yaml,
                     file="mydata.yaml",
                     ordered_dict=True)

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the contents of the file
    """
    kwargs = {}
    kwargs["typ"] = "rt" if ordered_dict else "safe"
    with open(file, "r") as f:
        yml = ruamel.yaml.YAML(pure=True, **kwargs)
        data = yml.load(f.read())

    return Result(host=task.host, result=data)
