import shlex
import subprocess


from nornir.core.exceptions import CommandError
from nornir.core.task import Result, Task


def command(task: Task, command: str) -> Result:
    """
    Executes a command locally

    Arguments:
        command: command to execute

    Returns:
        Result object with the following attributes set:
          * result (``str``): stderr or stdout
          * stdout (``str``): stdout
          * stderr (``str``): stderr

    Raises:
        :obj:`nornir.core.exceptions.CommandError`: when there is a command error
    """
    cmd = subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )

    stdout, stderr = cmd.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()

    if cmd.poll():
        raise CommandError(command, cmd.returncode, stdout, stderr)

    result = stderr if stderr else stdout
    return Result(result=result, host=task.host, stderr=stderr, stdout=stdout)
