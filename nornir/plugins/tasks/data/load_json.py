import json

from nornir.core.task import Result, Task


def load_json(task: Task, file: str) -> Result:
    """
    Loads a json file.

    Arguments:
        file: path to the file containing the json file to load

    Examples:

        Simple example with ``ordered_dict``::

            > nr.run(task=load_json,
                     file="mydata.json")

        file: path to the file containing the json file to load

    Returns:
        Result object with the following attributes set:
          * result (``dict``): dictionary with the contents of the file
    """
    with open(file, "r") as f:
        data = json.loads(f.read())

    return Result(host=task.host, result=data)
