from __future__ import unicode_literals

from nornir.core.task import Result, Task


def netmiko_commit(
    task: Task
) -> Result:
    """
    Execute Netmiko commit method

    Returns:
        :obj: `nornir.core.task.Result`:
          * result (``str``): String showing the CLI output from the commit operation
    """
    conn = task.host.get_connection("netmiko", task.nornir.config)
    result = conn.commit()
    return Result(host=task.host, result=result, changed=True)
