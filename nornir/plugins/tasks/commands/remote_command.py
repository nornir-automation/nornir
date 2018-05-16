from nornir.core.exceptions import CommandError
from nornir.core.task import Result


def remote_command(task, command):
    """
    Executes a command locally

    Arguments:
        command (``str``): command to execute

    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``str``): stderr or stdout
          * stdout (``str``): stdout
          * stderr (``srr``): stderr

    Raises:
        :obj:`nornir.core.exceptions.CommandError`: when there is a command error
    """
    client = task.host.get_connection("paramiko")

    chan = client.get_transport().open_session()
    chan.exec_command(command)

    exit_status_code = chan.recv_exit_status()

    with chan.makefile() as f:
        stdout = f.read().decode()
    with chan.makefile_stderr() as f:
        stderr = f.read().decode()

    if exit_status_code:
        raise CommandError(command, exit_status_code, stdout, stderr)

    result = stderr if stderr else stdout
    return Result(result=result, host=task.host, stderr=stderr, stdout=stdout)
