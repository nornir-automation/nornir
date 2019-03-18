from nornir.core.exceptions import CommandError
from nornir.core.task import Result, Task

from paramiko.agent import AgentRequestHandler


def remote_command(task: Task, command: str) -> Result:
    """
    Executes a command remotely on the host

    Arguments:
        command (``str``): command to execute

    Returns:
        Result object with the following attributes set:
          * result (``str``): stderr or stdout
          * stdout (``str``): stdout
          * stderr (``str``): stderr

    Raises:
        :obj:`nornir.core.exceptions.CommandError`: when there is a command error
    """
    client = task.host.get_connection("paramiko", task.nornir.config)
    connection_state = task.host.get_connection_state("paramiko")

    chan = client.get_transport().open_session()

    if connection_state["ssh_forward_agent"]:
        AgentRequestHandler(chan)

    chan.exec_command(command)

    with chan.makefile() as f:
        stdout = f.read().decode()
    with chan.makefile_stderr() as f:
        stderr = f.read().decode()

    exit_status_code = chan.recv_exit_status()

    if exit_status_code:
        raise CommandError(command, exit_status_code, stdout, stderr)

    result = stderr if stderr else stdout
    return Result(result=result, host=task.host, stderr=stderr, stdout=stdout)
