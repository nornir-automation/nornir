from typing import Optional

from nornir.core.task import Result, Task


def napalm_rollback(task: Task, rollback: bool = False) -> Result:
    """
    Rollback device configuration using napalm

    Arguments:
        rollback: whether to rollback the configuration or not
    """
    device = task.host.get_connection("napalm", task.nornir.config)

    if rollback:
        device.rollback()

    return Result(host=task.host)
