import getpass
import shlex
import subprocess


from brigade.core.exceptions import CommandError


def remote_command(task, command, ignore_keys=True):
    """
    Executes a command on remote host via ssh.

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
    ip = task.host.data.get("brigade_ip", task.host.name)
    username = task.host.data.get("brigade_username", getpass.getuser())
    password = task.host.data.get("brigade_password", "")
    port = task.host.data.get("brigade_port", 22)

    options = ""

    if ignore_keys:
        options += " -o 'StrictHostKeyChecking=no' "

    command = "sshpass -p '{}' ssh {} -p {} {}@{} {}".format(password, options,
                                                             port, username, ip, command)

    ssh = subprocess.Popen(shlex.split(command),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=False)

    stdout, stderr = ssh.communicate()

    if ssh.poll():
        raise CommandError(stderr, command, ssh.returncode, stdout, stderr)

    return {
         "result": stderr if stderr else stdout,
         "stderr": stderr,
         "stdout": stdout,
    }
