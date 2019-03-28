import base64
import difflib
import threading
from typing import Tuple

from nornir.core.task import Result, Task

import requests


LOCK = threading.Lock()


def _generate_diff(original: str, fromfile: str, tofile: str, content: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(), content.splitlines(), fromfile=fromfile, tofile=tofile
    )
    return "\n".join(diff)


def _get_repository(session: requests.Session, url: str, repository: str) -> int:
    resp = session.get(f"{url}/api/v4/projects?search={repository}")
    if resp.status_code != 200:
        raise RuntimeError(f"Unexpected Gitlab status code {resp.status_code}")

    pid = 0
    found = False
    respjson = resp.json()
    if not len(respjson):
        raise RuntimeError("Gitlab repository not found")

    for p in respjson:
        if p.get("name", "") == repository:
            found = True
            pid = p.get("id", 0)

    if not pid or not found:
        raise RuntimeError("Gitlab repository not found")

    return pid


def _remote_exists(
    task: Task,
    session: requests.Session,
    url: str,
    pid: int,
    filename: str,
    branch: str,
) -> Tuple[bool, str]:
    resp = session.get(
        f"{url}/api/v4/projects/{pid}/repository/files/{filename}?ref={branch}"
    )
    if resp.status_code == 200:
        return (
            True,
            base64.decodebytes(resp.json()["content"].encode("ascii")).decode(),
        )
    return (False, "")


def _create(
    task: Task,
    session: requests.Session,
    url: str,
    pid: int,
    filename: str,
    content: str,
    branch: str,
    commit_message: str,
    dry_run: bool,
) -> str:
    if dry_run:
        return _generate_diff("", "", filename, content)

    with LOCK:
        url = f"{url}/api/v4/projects/{pid}/repository/files/{filename}"
        data = {"branch": branch, "content": content, "commit_message": commit_message}
        resp = session.post(url, data=data)

        if resp.status_code != 201:
            raise RuntimeError(f"Unable to create file: {filename}!")
    return _generate_diff("", "", filename, content)


def _update(
    task: Task,
    session: requests.Session,
    url: str,
    pid: int,
    filename: str,
    content: str,
    branch: str,
    commit_message: str,
    dry_run: bool,
) -> str:
    exists, original = _remote_exists(task, session, url, pid, filename, branch)

    if not exists:
        raise RuntimeError(f"File '{filename}' does not exist!")

    if dry_run:
        return _generate_diff(original, filename, filename, content)

    if original != content:
        with LOCK:
            url = f"{url}/api/v4/projects/{pid}/repository/files/{filename}"
            data = {
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
            }
            resp = session.put(url=url, data=data)
            if resp.status_code != 200:
                print(f"{resp.status_code} : {resp.text}")
                raise RuntimeError(f"Unable to update file: {filename}")
    return _generate_diff(original, filename, filename, content)


def gitlab(
    task: Task,
    url: str,
    token: str,
    repository: str,
    filename: str,
    content: str,
    action: str = "create",
    dry_run: bool = False,
    branch: str = "master",
    commit_message: str = "",
) -> Result:
    """
    Writes contents to a new file or update contents of an existing file in a
    gitlab repository.

    Example:

        nornir.run(files.gitlab,
                   action="create",
                   url="https://gitlab.localhost.com",
                   token="ABCD1234",
                   repository="test",
                   filename="config",
                   branch="master")

    Arguments:
        dry_run: Whether to apply changes or not
        url: Gitlab instance URL
        token: Personal access token
        repository: destination repository
        filename: destination file name
        content: content to write
        action: ``create``, ``update``
        update: Update the file if it already exists,
                when create action is used.
        branch: destination branch

    Returns:
        Result object with the following attributes set:
            * changed (``bool``):
            * diff (``str``): unified diff

    """
    dry_run = task.is_dry_run(dry_run)

    session = requests.session()
    session.headers.update({"PRIVATE-TOKEN": token})

    if commit_message == "":
        commit_message = "File created with nornir"

    pid = _get_repository(session, url, repository)

    if action == "create":
        diff = _create(
            task, session, url, pid, filename, content, branch, commit_message, dry_run
        )
    elif action == "update":
        diff = _update(
            task, session, url, pid, filename, content, branch, commit_message, dry_run
        )
    return Result(host=task.host, diff=diff, changed=bool(diff))
