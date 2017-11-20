import json

from brigade.core.helpers import format_string


def load_json(task, file):
    """
    Loads a json file.

    Arguments:
        file (str): path to the file containing the json file to load

    Returns:
        dictionary:
          * result (``dict``): dictionary with the contents of the file
    """
    file = format_string(file, task)
    with open(file, 'r') as f:
        data = json.loads(f.read())

    return {
        "result": data
    }
