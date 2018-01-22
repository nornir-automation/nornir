from brigade.core.exceptions import CommandError
from brigade.core.task import Result


def remote_command(task, command):
    """
    Executes a command locally

    Arguments:
        command (``str``): command to execute

    Returns:
        :obj:`brigade.core.task.Result`:
          * stdout (``str``): stdout
          * stderr (``srr``): stderr

    Raises:
        :obj:`brigade.core.exceptions.CommandError`: when there is a command error
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

    return Result(host=task.host, stderr=stderr, stdout=stdout)
