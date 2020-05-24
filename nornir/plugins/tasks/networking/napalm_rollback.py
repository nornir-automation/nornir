from nornir.core.task import Result, Task


def napalm_rollback(task: Task, dry_run: bool = None) -> Result:
    """
    Rollback device configuration using napalm
    Arguments:
        dry_run: whether to rollback the configuration or not
    """
    device = task.host.get_connection("napalm", task.nornir.config)

    if not dry_run:
        device.rollback()

    return Result(host=task.host)
