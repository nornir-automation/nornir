import errno
import yaml

from brigade.core.exceptions import FileError
from brigade.core.helpers import format_string
from brigade.core.task import Result


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
    try:
        with open(file, 'r') as f:
            data = yaml.load(f.read())
    except IOError as e:
        if e.errno == errno.ENOENT:
            raise FileError(file, 'Unable to load file')
    except yaml.YAMLError as e:
        raise yaml.YAMLError()

    return Result(host=task.host, result=data)
