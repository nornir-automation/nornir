from typing import Any

from netmiko import file_transfer

from nornir.core.task import Result, Task


def netmiko_file_transfer(
    task: Task, source_file: str, dest_file: str, **kwargs: Any
) -> Result:
    """
    Execute Netmiko file_transfer method

    Arguments:
        source_file: Source file.
        dest_file: Destination file.
        kwargs: Additional arguments to pass to file_transfer

    Returns:
        Result object with the following attributes set:
          * result (``bool``): file exists and MD5 is valid
          * changed (``bool``): the destination file was changed

    """
    net_connect = task.host.get_connection("netmiko", task.nornir.config)
    kwargs.setdefault("direction", "put")
    scp_result = file_transfer(
        net_connect, source_file=source_file, dest_file=dest_file, **kwargs
    )
    if kwargs.get("disable_md5") is True:
        file_valid = scp_result["file_exists"]
    else:
        file_valid = scp_result["file_exists"] and scp_result["file_verified"]
    return Result(
        host=task.host, result=file_valid, changed=scp_result["file_transferred"]
    )
