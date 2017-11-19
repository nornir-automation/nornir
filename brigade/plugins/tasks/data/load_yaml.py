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
    file = file.format(host=task.host, **task.host)
    with open(file, 'r') as f:
        data = yaml.load(f.read())

    return {
        "result": data
    }
