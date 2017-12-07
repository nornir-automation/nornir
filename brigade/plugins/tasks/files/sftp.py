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


def _get(task, sftp_client, src, dst, path=None):
    remote_hash = get_remote_hash(task, src)
    try:
        local_hash = get_local_hash(dst)
        same = remote_hash == local_hash
    except IOError:
        same = False

    if not same and not task.dry_run:
        sftp_client.get(src, dst)

    return not same


def get(task, sftp_client, src, dst, *args, **kwargs):
    try:
        commands.remote_command(task, "test -f {}".format(src))
        is_file = True
    except CommandError:
        is_file = False

    if is_file:
        changed = _get(task, sftp_client, src, dst)
        files_changed = [dst] if changed else []
    else:
        create_local_dir(dst)
        changed = False
        files_changed = []
        for f in sftp_client.listdir_attr(src):
            s = os.path.join(src, f.filename)
            d = os.path.join(dst, f.filename)
            if f.longname[0] == 'd':
                # it's a directory
                files_changed.extend(get(task, sftp_client, s, d, *args, **kwargs))
            else:
                rc = _get(task, sftp_client, s, d)
                changed = changed or rc
                if rc:
                    files_changed.append(d)

    return files_changed


def _put(task, sftp_client, src, dst, path=None):
    if path and not task.dry_run:
        create_remote_dir(sftp_client, path)

    if path:
        dst = os.path.join(path, dst)

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

    return not same


def create_local_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def create_remote_dir(sftp_client, directory):
    try:
        sftp_client.listdir(directory)
    except IOError:
        sftp_client.mkdir(directory)


def put(task, sftp_client, src, dst, *args, **kwargs):
    if os.path.isdir(src):
        dst = sftp_client.normalize(dst)
        create_remote_dir(sftp_client, dst)
        files_changed = []
        for path, _, files in os.walk(src):
            for f in files:
                s = os.path.join(path, f)
                p = os.path.join(dst, path)
                rc = _put(task, sftp_client, s, f, p)
                if rc:
                    files_changed.append(dst)
    else:
        changed = _put(task, sftp_client, src, dst)
        files_changed = [dst] if changed else []

    return files_changed


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
          * files_changed (``list``): list of files that changed
    """
    src = format_string(src, task, **task.host)
    dst = format_string(dst, task, **task.host)
    actions = {
        "put": put,
        "get": get,
    }
    client = task.host.ssh_connection
    sftp_client = paramiko.SFTPClient.from_transport(client.get_transport())
    files_changed = actions[action](task, sftp_client, src, dst)
    return Result(host=task.host, changed=bool(files_changed), files_changed=files_changed)
