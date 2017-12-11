from brigade.core.task import Result


def napalm_configure(task, configuration, replace=False):
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

    if replace:
        device.load_replace_candidate(config=configuration)
    else:
        device.load_merge_candidate(config=configuration)
    diff = device.compare_config()

    if task.dry_run:
        device.discard_config()
    else:
        device.commit_config()
    return Result(host=task.host, diff=diff, changed=len(diff) > 0)
