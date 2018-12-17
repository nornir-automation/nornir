import hashlib
import os
import stat
from typing import List, Optional

from nornir.core.exceptions import CommandError
from nornir.core.task import Result, Task
from nornir.plugins.tasks import commands

import paramiko

from scp import SCPClient


def get_src_hash(filename: str) -> str:
    sha1sum = hashlib.sha1()

    with open(filename, "rb") as f:
        block = f.read(2 ** 16)
        while len(block) != 0:
            sha1sum.update(block)
            block = f.read(2 ** 16)
    return sha1sum.hexdigest()


def get_dst_hash(task: Task, filename: str) -> str:
    command = "sha1sum {}".format(filename)
    try:
        result = commands.remote_command(task, command)
        if result.stdout is not None:
            return result.stdout.split()[0]

    except CommandError as e:
        if "No such file or directory" in e.stderr:
            return ""

        raise

    return ""


def remote_exists(sftp_client: paramiko.SFTPClient, f: str) -> bool:
    try:
        sftp_client.stat(f)
        return True

    except IOError:
        return False


def compare_put_files(
    task: Task, sftp_client: paramiko.SFTPClient, src: str, dst: str
) -> List[str]:
    changed = []
    if os.path.isfile(src):
        src_hash = get_src_hash(src)
        try:
            dst_hash = get_dst_hash(task, dst)
        except IOError:
            dst_hash = ""
        if src_hash != dst_hash:
            changed.append(dst)
    else:
        if remote_exists(sftp_client, dst):
            for f in os.listdir(src):
                s = os.path.join(src, f)
                d = os.path.join(dst, f)
                changed.extend(compare_put_files(task, sftp_client, s, d))
        else:
            changed.append(dst)
    return changed


def compare_get_files(
    task: Task, sftp_client: paramiko.SFTPClient, src: str, dst: str
) -> List[str]:
    changed = []
    if stat.S_ISREG(sftp_client.stat(src).st_mode):
        # is a file
        src_hash = get_dst_hash(task, src)
        try:
            dst_hash = get_src_hash(dst)
        except IOError:
            dst_hash = ""
        if src_hash != dst_hash:
            changed.append(dst)
    else:
        if os.path.exists(dst):
            for f in sftp_client.listdir(src):
                s = os.path.join(src, f)
                d = os.path.join(dst, f)
                changed.extend(compare_get_files(task, sftp_client, s, d))
        else:
            changed.append(dst)
    return changed


def get(
    task: Task,
    scp_client: SCPClient,
    sftp_client: paramiko.SFTPClient,
    src: str,
    dst: str,
    dry_run: Optional[bool] = None,
) -> List[str]:
    changed = compare_get_files(task, sftp_client, src, dst)
    if changed and not dry_run:
        scp_client.get(src, dst, recursive=True)
    return changed


def put(
    task: Task,
    scp_client: SCPClient,
    sftp_client: paramiko.SFTPClient,
    src: str,
    dst: str,
    dry_run: Optional[bool] = None,
) -> List[str]:
    changed = compare_put_files(task, sftp_client, src, dst)
    if changed and not dry_run:
        scp_client.put(src, dst, recursive=True)
    return changed


def sftp(
    task: Task, src: str, dst: str, action: str, dry_run: Optional[bool] = None
) -> Result:
    """
    Transfer files from/to the device using sftp protocol

    Example::

        nornir.run(files.sftp,
                    action="put",
                    src="README.md",
                    dst="/tmp/README.md")

    Arguments:
        dry_run: Whether to apply changes or not
        src: source file
        dst: destination
        action: ``put``, ``get``.

    Returns:
        Result object with the following attributes set:
          * changed (``bool``):
          * files_changed (``list``): list of files that changed
    """
    dry_run = task.is_dry_run(dry_run)
    actions = {"put": put, "get": get}
    client = task.host.get_connection("paramiko", task.nornir.config)
    scp_client = SCPClient(client.get_transport())
    sftp_client = paramiko.SFTPClient.from_transport(client.get_transport())
    files_changed = actions[action](task, scp_client, sftp_client, src, dst, dry_run)
    return Result(
        host=task.host, changed=bool(files_changed), files_changed=files_changed
    )
