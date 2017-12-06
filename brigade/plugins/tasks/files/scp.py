import hashlib
import logging

from brigade.core.task import Result
from brigade.plugins.tasks import commands

import paramiko


logger = logging.getLogger("brigade")


def get_local_hash(filename):
    sha1sum = hashlib.sha1()

    with open(filename, 'rb') as f:
        block = f.read(2**16)
        while len(block) != 0:
            sha1sum.update(block)
            block = f.read(2**16)
    return sha1sum.hexdigest()


def get_remote_hash(task, filename):
    command = "sha1sum {}".format(filename)
    result = commands.remote_command(task, command)
    return result.stdout.split()[0]


def scp(task, src, dst):
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
    client = task.host.ssh_connection()
    sftp = paramiko.SFTPClient.from_transport(client.get_transport())

    try:
        f = sftp.file(dst)
        found = True
    except IOError:
        found = False

    if found:
        remote_hash = get_remote_hash(task, dst)
        f.close()
        local_hash = get_local_hash(src)
        same = remote_hash == local_hash
    else:
        same = False

    if not same and not task.dry_run:
        sftp.put(src, dst)

    return Result(host=task.host, changed=not same)
