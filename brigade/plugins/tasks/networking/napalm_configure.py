from brigade.core.helpers import format_string
from brigade.core.task import Result


def napalm_configure(task, filename=None, configuration=None, replace=False):
    """
    Loads configuration into a network devices using napalm

    Arguments:
        configuration (str): configuration to load into the device
        replace (bool): whether to replace or merge the configuration

    Returns:
        :obj:`brigade.core.task.Result`:
          * changed (``bool``): whether if the task is changing the system or not
          * diff (``string``): change in the system
    """
    device = task.host.get_connection("napalm")
    filename = format_string(filename, task, **task.host) if filename is not None else None

    if replace:
        device.load_replace_candidate(filename=filename, config=configuration)
    else:
        device.load_merge_candidate(filename=filename, config=configuration)
    diff = device.compare_config()

    if not task.dry_run and diff:
        device.commit_config()
    else:
        device.discard_config()
    return Result(host=task.host, diff=diff, changed=len(diff) > 0)
