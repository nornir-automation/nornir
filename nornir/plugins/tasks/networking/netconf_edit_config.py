from nornir.core.task import Result, Task


def netconf_edit_config(task: Task, config: str, target: str = "running") -> Result:
    """
    Edit configuration of device using Netconf

    Arguments:
        config: Configuration snippet to apply
        target: Target configuration store

    Examples:

        Simple example::

            > nr.run(task=netconf_edit_config, config=desired_config)

    """
    manager = task.host.get_connection("netconf", task.nornir.config)
    manager.edit_config(config, target=target)

    return Result(host=task.host)
