import logging

from brigade.core.exceptions import CommandError
from brigade.core.task import Result


logger = logging.getLogger("brigade")


def remote_command(task, command, ssh_config_file=None, ssh_key_file=None):
    """
    Executes a command locally

    Arguments:
        command (``str``): command to execute

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``str``): stderr or stdout
          * stdout (``str``): stdout
          * stderr (``srr``): stderr
    Raises:
        :obj:`brigade.core.exceptions.CommandError`: when there is a command error
    """
    client = task.host.ssh_connection(ssh_config_file, ssh_key_file)

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
