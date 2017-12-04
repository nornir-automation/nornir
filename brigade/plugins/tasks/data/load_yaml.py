from brigade.core.helpers import format_string
from brigade.core.task import Result


import yaml


def load_yaml(task, file):
    """
    Loads a yaml file.

    Arguments:
        file (str): path to the file containing the yaml file to load

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the contents of the file
    """
    file = format_string(file, task)
    with open(file, 'r') as f:
        data = yaml.load(f.read())

    return Result(host=task.host, result=data)
