from nornir.core.task import Result, Task


def echo_data(task: Task, **kwargs):
    """
    Dummy task that echoes the data passed to it. Useful in grouped_tasks
    to debug data passed to tasks.

    Arguments:
        ``**kwargs``: Any <key,value> pair you want

    Returns:
        Result object with the following attributes set:
          * result (``dict``): ``**kwargs`` passed to the task
    """
    return Result(host=task.host, result=kwargs)
