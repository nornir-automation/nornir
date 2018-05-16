from nornir.core.task import Result


def napalm_configure(
    task, dry_run=None, filename=None, configuration=None, replace=False
):
    """
    Loads configuration into a network devices using napalm

    Arguments:
        dry_run (bool): Whether to apply changes or not
        configuration (str): configuration to load into the device
        filename (str): filename containing the configuration to load into the device
        replace (bool): whether to replace or merge the configuration

    Returns:
        :obj:`nornir.core.task.Result`:
          * changed (``bool``): whether if the task is changing the system or not
          * diff (``string``): change in the system
    """
    device = task.host.get_connection("napalm")

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
