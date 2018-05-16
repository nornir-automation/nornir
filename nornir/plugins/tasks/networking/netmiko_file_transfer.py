from nornir.core.task import Result

from netmiko import file_transfer


def netmiko_file_transfer(task, source_file, dest_file, **kwargs):
    """
    Execute Netmiko file_transfer method

    Arguments:
        source_file(str): Source file.
        dest_file(str): Destination file.
        kwargs (dict, optional): Additional arguments to pass to file_transfer

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``bool``): file exists and MD5 is valid
          * changed (``bool``): the destination file was changed

    """
    net_connect = task.host.get_connection("netmiko")
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
