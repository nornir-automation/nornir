from brigade.core.helpers import format_string

import yaml


def load_yaml(task, file):
    """
    Loads a yaml file.

    Arguments:
        file (str): path to the file containing the yaml file to load

    Returns:
        dictionary:
          * result (``dict``): dictionary with the contents of the file
    """
    file = format_string(file, task)
    with open(file, 'r') as f:
        data = yaml.load(f.read())

    return {
        "result": data
    }
