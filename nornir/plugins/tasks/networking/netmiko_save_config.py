from __future__ import unicode_literals

from nornir.core.task import Result, Task


def netmiko_save_config(
    task: Task, cmd: str = "", confirm: bool = False, confirm_response: str = ""
) -> Result:
    """
    Execute Netmiko save_config method

    Arguments:
        cmd(str, optional): Command used to save the configuration.
        confirm(bool, optional): Does device prompt for confirmation before executing save operation
        confirm_response(str, optional): Response send to device when it prompts for confirmation

    Returns:
        :obj: `nornir.core.task.Result`:
          * result (``str``): String showing the CLI output from the save operation
    """
    conn = task.host.get_connection("netmiko", task.nornir.config)
    if cmd:
        result = conn.save_config(
            cmd=cmd, confirm=confirm, confirm_response=confirm_response
        )
    else:
        result = conn.save_config(confirm=confirm, confirm_response=confirm_response)
    return Result(host=task.host, result=result, changed=True)
