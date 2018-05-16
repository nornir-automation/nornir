import json

from nornir.core.task import Result


def load_json(task, file):
    """
    Loads a json file.

    Arguments:
        file (str): path to the file containing the json file to load

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): dictionary with the contents of the file
    """
    with open(file, "r") as f:
        data = json.loads(f.read())

    return Result(host=task.host, result=data)
