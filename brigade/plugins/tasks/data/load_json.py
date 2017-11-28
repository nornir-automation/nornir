import errno
import json

from brigade.core.exceptions import FileError
from brigade.core.helpers import format_string
from brigade.core.task import Result


def load_json(task, file):
    """
    Loads a json file.

    Arguments:
        file (str): path to the file containing the json file to load

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the contents of the file
    """
    file = format_string(file, task)
    try:
        with open(file, 'r') as f:
            data = json.loads(f.read())
    except IOError as e:
        if e.errno == errno.ENOENT:
            raise FileError(file, 'Unable to load file')
    except Exception as e:
        if issubclass(e.__class__, ValueError):
            raise FileError(file, 'Unable to parse json: {}'.format(e.__str__()))

    return Result(host=task.host, result=data)
