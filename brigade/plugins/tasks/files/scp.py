import logging
import shlex
import subprocess


from brigade.core.exceptions import CommandError
from brigade.core.helpers import format_string
from brigade.core.task import Result


logger = logging.getLogger("brigade")


def scp(task, src, dst, ignore_keys=True):
    """
    Runs scp on the local machine. You can use variables in the path.

    Example::

        brigade.run(files.scp,
                    ignore_keys=True,
                    src=local_path,
                    dst="{brigade_ip}:" + remote_path)

    Arguments:
        src (``str``): source for scp command
        dst (``str``): destination for scp command

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``str``): stderr or stdout
          * stdout (``str``): stdout
          * stderr (``srr``): stderr
    Raises:
        :obj:`brigade.core.exceptions.CommandError`: when there is a command error
    """
    src = format_string(src, task, **task.host)
    dst = format_string(dst, task, **task.host)

    options = " -o 'User={}' ".format(task.host.username)

    if ignore_keys:
        options += " -o 'StrictHostKeyChecking=no' "

    command = "sshpass -p '{h.password}' scp -r {options} -P {h.ssh_port} \
            {src} {dst}".format(h=task.host, options=options, src=src, dst=dst)

    logger.debug("{}:cmd:{}".format(task.host, command))
    ssh = subprocess.Popen(shlex.split(command),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=False)

    stdout, stderr = ssh.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()

    if ssh.poll():
        raise CommandError(command, ssh.returncode, stdout, stderr)

    result = stderr if stderr else stdout
    return Result(result=result, host=task.host, stderr=stderr, stdout=stdout)
