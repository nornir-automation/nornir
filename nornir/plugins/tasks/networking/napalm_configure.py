from typing import Optional

from nornir.core.task import Result, Task


def napalm_configure(
    task: Task,
    dry_run: Optional[bool] = None,
    filename: Optional[str] = None,
    configuration: Optional[str] = None,
    replace: bool = False,
) -> Result:
    """
    Loads configuration into a network devices using napalm

    Arguments:
        dry_run: Whether to apply changes or not
        filename: filename containing the configuration to load into the device
        configuration: configuration to load into the device
        replace: whether to replace or merge the configuration

    Returns:
        Result object with the following attributes set:
          * changed (``bool``): whether the task is changing the system or not
          * diff (``string``): change in the system
    """
    device = task.host.get_connection("napalm", task.nornir.config)

    if replace:
        device.load_replace_candidate(filename=filename, config=configuration)
    else:
        device.load_merge_candidate(filename=filename, config=configuration)
    diff = device.compare_config()

    dry_run = task.is_dry_run(dry_run)
    if not dry_run and diff:
        device.commit_config()
    else:
        device.discard_config()
    return Result(host=task.host, diff=diff, changed=len(diff) > 0)
