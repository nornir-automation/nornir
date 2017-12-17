from brigade.core.task import Result


def write(task, filename, content, append=False):
    """
    TBD
    """
    mode = "a+" if append else "w+"
    with open(filename, mode=mode) as f:
        f.write(content)

    return Result(host=task.host)
