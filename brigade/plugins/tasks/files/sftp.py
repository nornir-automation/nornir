import hashlib
import logging
import os

from brigade.core.exceptions import CommandError
from brigade.core.helpers import format_string
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


def get(task, sftp_client, src, dst, *args, **kwargs):
    try:
        commands.remote_command(task, "test -f {}".format(src))
        is_file = True
    except CommandError:
        is_file = False

    if is_file:
        remote_hash = get_remote_hash(task, src)
        try:
            local_hash = get_local_hash(dst)
            same = remote_hash == local_hash
        except IOError:
            same = False
    else:
        same = False

    if not same and not task.dry_run:
        sftp_client.get(src, dst)

    return Result(host=task.host, changed=not same)


def put(task, sftp_client, src, dst, *args, **kwargs):
    if os.path.isdir(src):
        same = False
    else:
        try:
            f = sftp_client.file(dst)
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
        sftp_client.put(src, dst)

    return Result(host=task.host, changed=not same)


def sftp(task, src, dst, action):
    """
    Transfer files from/to the device using sftp protocol

    Example::

        brigade.run(files.sftp,
                    action="put",
                    src="README.md",
                    dst="/tmp/README.md")

    Arguments:
        src (``str``): source file
        dst (``str``): destination
        action (``str``): ``put``, ``get``.

    Returns:
        :obj:`brigade.core.task.Result`:
          * changed (``bool``):
    """
    src = format_string(src, task, **task.host)
    dst = format_string(dst, task, **task.host)
    actions = {
        "put": put,
        "get": get,
    }
    client = task.host.ssh_connection
    sftp_client = paramiko.SFTPClient.from_transport(client.get_transport())

    return actions[action](task, sftp_client, src, dst)
