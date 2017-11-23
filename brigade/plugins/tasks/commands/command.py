import logging
import shlex
import subprocess


from brigade.core.exceptions import CommandError


logger = logging.getLogger("brigade")


def command(task, command):
    """
    Executes a command locally

    Arguments:
        command (``str``): command to execute

    Returns:
        dictionary:
          * result (``str``): stderr or stdout
          * stdout (``str``): stdout
          * stderr (``srr``): stderr
    Raises:
        :obj:`brigade.core.exceptions.CommandError`: when there is a command error
    """
    logger.debug("{}:local_cmd:{}".format(task.host, command))
    cmd = subprocess.Popen(shlex.split(command),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=False)

    stdout, stderr = cmd.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()

    if cmd.poll():
        raise CommandError(command, cmd.returncode, stdout, stderr)

    return {
         "result": stderr if stderr else stdout,
         "stderr": stderr,
         "stdout": stdout,
    }
