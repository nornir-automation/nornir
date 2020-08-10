import base64
import difflib
import threading

from pathlib import Path
from typing import Tuple
from urllib.parse import quote

from nornir.core.task import Optional, Result, Task

import requests


LOCK = threading.Lock()


def _generate_diff(original: str, fromfile: str, tofile: str, content: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(), content.splitlines(), fromfile=fromfile, tofile=tofile
    )
    return "\n".join(diff)


def _remote_exists(
    task: Task,
    session: requests.Session,
    url: str,
    repository: str,
    filename: str,
    ref: str,
) -> Tuple[bool, str]:
    quoted_repository = quote(repository, safe="")
    quoted_filename = quote(filename, safe="")
    resp = session.get(
        f"{url}/api/v4/projects/{quoted_repository}/repository/files/{quoted_filename}?ref={ref}"
    )
    if resp.status_code == 200:
        return (
            True,
            base64.decodebytes(resp.json()["content"].encode("ascii")).decode(),
        )
    return (False, "")


def _local_exists(task: Task, filename: str) -> Tuple[bool, str]:
    try:
        with open(Path(filename)) as f:
            content = f.read()
        return (True, content)
    except FileNotFoundError:
        return (False, "")


def _create(
    task: Task,
    session: requests.Session,
    url: str,
    repository: str,
    filename: str,
    content: str,
    branch: str,
    commit_message: str,
    dry_run: bool,
) -> str:
    quoted_repository = quote(repository, safe="")
    quoted_filename = quote(filename, safe="")
    if dry_run:
        return _generate_diff("", "", filename, content)

    with LOCK:
        url = f"{url}/api/v4/projects/{quoted_repository}/repository/files/{quoted_filename}"
        data = {"branch": branch, "content": content, "commit_message": commit_message}
        resp = session.post(url, data=data)

        if resp.status_code != 201:
            raise RuntimeError(f"Unable to create file: {filename}!")
    return _generate_diff("", "", filename, content)


def _update(
    task: Task,
    session: requests.Session,
    url: str,
    repository: str,
    filename: str,
    content: str,
    branch: str,
    commit_message: str,
    dry_run: bool,
) -> str:

    quoted_repository = quote(repository, safe="")
    quoted_filename = quote(filename, safe="")
    exists, original = _remote_exists(task, session, url, repository, filename, branch)

    if not exists:
        raise RuntimeError(f"File '{filename}' does not exist!")

    if dry_run:
        return _generate_diff(original, filename, filename, content)

    if original != content:
        with LOCK:
            url = f"{url}/api/v4/projects/{quoted_repository}/repository/files/{quoted_filename}"
            data = {
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
            }
            resp = session.put(url=url, data=data)
            if resp.status_code != 200:
                raise RuntimeError(f"Unable to update file: {filename}")
    return _generate_diff(original, filename, filename, content)


def _get(
    task: Task,
    session: requests.Session,
    url: str,
    repository: str,
    filename: str,
    destination: str,
    ref: str,
    dry_run: bool,
) -> str:

    # if destination is not provided, use the filename as destination in current
    # directory
    if destination == "":
        destination = filename

    (_, local) = _local_exists(task, destination)

    (status, content) = _remote_exists(task, session, url, repository, filename, ref)

    if not status:
        raise RuntimeError(f"Unable to get file: {filename}")

    if not dry_run:
        if local != content:
            with open(destination, "w") as f:
                f.write(content)

    return _generate_diff(local, destination, destination, content)


def gitlab(
    task: Task,
    url: str,
    token: str,
    repository: str,
    filename: str,
    content: str = "",
    action: str = "create",
    dry_run: Optional[bool] = None,
    branch: str = "master",
    destination: str = "",
    ref: str = "master",
    commit_message: str = "",
) -> Result:
    """
    Exposes some of the Gitlab API functionality for operations on files
    in a Gitlab repository.

    Example:

        nornir.run(files.gitlab,
                   action="create",
                   url="https://gitlab.localhost.com",
                   token="ABCD1234",
                   repository="test",
                   filename="config",
                   ref="master")

    Arguments:
        dry_run: Whether to apply changes or not
        url: Gitlab instance URL
        token: Personal access token
        repository: source/destination repository
        filename: source/destination file name
        content: content to write
        action: ``create``, ``update``, ``get``
        branch: destination branch
        destination: local destination filename (only used in get action)
        ref: branch, commit hash or tag (only used in get action)
        commit_message: commit message

    Returns:
        Result object with the following attributes set:
            * changed (``bool``):
            * diff (``str``): unified diff

    """
    dry_run = dry_run if dry_run is not None else task.is_dry_run()

    session = requests.session()
    session.headers.update({"PRIVATE-TOKEN": token})

    if commit_message == "":
        commit_message = "File created with nornir"

    if action == "create":
        diff = _create(
            task,
            session,
            url,
            repository,
            filename,
            content,
            branch,
            commit_message,
            dry_run,
        )
    elif action == "update":
        diff = _update(
            task,
            session,
            url,
            repository,
            filename,
            content,
            branch,
            commit_message,
            dry_run,
        )
    elif action == "get":
        diff = _get(task, session, url, repository, filename, destination, ref, dry_run)
    return Result(host=task.host, diff=diff, changed=bool(diff))
