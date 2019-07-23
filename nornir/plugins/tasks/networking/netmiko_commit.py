from __future__ import unicode_literals

from typing import Any

from nornir.core.task import Result, Task


def netmiko_commit(task: Task, **kwargs: Any) -> Result:
    """
    Execute Netmiko commit method

    Arguments:
        kwargs: Additional arguments to pass to method.

    Returns:
        :obj: `nornir.core.task.Result`:
          * result (``str``): String showing the CLI output from the commit operation
    """
    conn = task.host.get_connection("netmiko", task.nornir.config)
    result = conn.commit(**kwargs)
    return Result(host=task.host, result=result, changed=True)
