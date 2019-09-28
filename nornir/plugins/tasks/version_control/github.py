import base64
import difflib
import logging
import threading
from pathlib import Path
from typing import Tuple

from nornir.core.task import Optional, Result, Task

import requests


LOCK = threading.Lock()


def _generate_diff(original: str, fromfile: str, tofile: str, content: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(), content.splitlines(), fromfile=fromfile, tofile=tofile
    )
    return "\n".join(diff)


def _repo_exists(
    task: Task, session: requests.Session, url: str, owner: str, repository: str
) -> bool:
    resp = session.get(f"{url}/repos/{owner}/{repository}")
    if resp.status_code == 200:
        return True
    return False


def _branch_exists(
    task: Task,
    session: requests.Session,
    url: str,
    owner: str,
    repository: str,
    branch: str,
) -> bool:
    resp = session.get(f"{url}/repos/{owner}/{repository}/branches/{branch}")
    if resp.status_code == 200:
        return True
    return False


def _ref_exists(
    task: Task,
    session: requests.Session,
    url: str,
    owner: str,
    repository: str,
    ref: str,
) -> bool:
    resp = session.get(f"{url}/repos/{owner}/{repository}/commits/{ref}")
    if resp.status_code == 200:
        return True
    return False


def _remote_file_exists(
    task: Task,
    session: requests.Session,
    url: str,
    owner: str,
    repository: str,
    filename: str,
    ref: str,
) -> Tuple[bool, str, str]:
    resp = session.get(
        f"{url}/repos/{owner}/{repository}/contents/{filename}?ref={ref}"
    )
    if resp.status_code == 200:
        return (
            True,
            base64.decodebytes(resp.json()["content"].encode("ascii")).decode(),
            resp.json()["sha"],
        )
    return (False, "", "")


def _local_file_exists(task: Task, filename: str) -> Tuple[bool, str]:
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
    owner: str,
    repository: str,
    filename: str,
    content: str,
    branch: str,
    commit_message: str,
    dry_run: bool,
) -> str:
    exists = _repo_exists(task, session, url, owner, repository)

    if not exists:
        raise RuntimeError(f"Repository '{repository}' does not exist!")

    exists = _branch_exists(task, session, url, owner, repository, branch)

    if not exists:
        raise RuntimeError(f"Branch '{branch}' does not exist!")

    (exists, _, _) = _remote_file_exists(
        task, session, url, owner, repository, filename, branch
    )

    if exists:
        raise RuntimeError(f"File '{filename}' already exists!")

    if dry_run:
        return _generate_diff("", "", filename, content)

    with LOCK:
        url = f"{url}/repos/{owner}/{repository}/contents/{filename}"
        data = {
            "branch": branch,
            "content": base64.b64encode(content.encode()).decode("ascii"),
            "message": commit_message,
        }
        resp = session.put(url, json=data)

        if resp.status_code != 201:
            print(resp.json())
            raise RuntimeError(f"Unable to create file: {filename}!")
    return _generate_diff("", "", filename, content)


def _update(
    task: Task,
    session: requests.Session,
    url: str,
    owner: str,
    repository: str,
    filename: str,
    content: str,
    branch: str,
    commit_message: str,
    dry_run: bool,
) -> str:
    exists = _repo_exists(task, session, url, owner, repository)

    if not exists:
        raise RuntimeError(f"Repository '{repository}' does not exist!")

    exists = _branch_exists(task, session, url, owner, repository, branch)

    if not exists:
        raise RuntimeError(f"Branch '{branch}' does not exist!")

    (exists, original, sha) = _remote_file_exists(
        task, session, url, owner, repository, filename, branch
    )

    if not exists:
        raise RuntimeError(f"File '{filename}' does not exist!")

    if dry_run:
        return _generate_diff(original, filename, filename, content)

    if original != content:
        with LOCK:
            url = f"{url}/repos/{owner}/{repository}/contents/{filename}"
            data = {
                "branch": branch,
                "content": base64.b64encode(content.encode()).decode("ascii"),
                "message": commit_message,
                "sha": sha,
            }
            resp = session.put(url=url, json=data)
            print(resp)
            if resp.status_code != 200:
                raise RuntimeError(f"Unable to update file: {filename}")
    return _generate_diff(original, filename, filename, content)


def _get(
    task: Task,
    session: requests.Session,
    url: str,
    owner: str,
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

    (_, local) = _local_file_exists(task, destination)

    exists = _repo_exists(task, session, url, owner, repository)

    if not exists:
        raise RuntimeError(f"Repository '{repository}' does not exist!")

    exists = _ref_exists(task, session, url, owner, repository, ref)

    if not exists:
        raise RuntimeError(f"Reference '{repository}' does not exist!")

    (exists, content, _) = _remote_file_exists(
        task, session, url, owner, repository, filename, ref
    )

    if not exists:
        raise RuntimeError(f"File '{filename}' does not exist!")

    if not dry_run:
        if local != content:
            with open(destination, "w") as f:
                f.write(content)

    return _generate_diff(local, destination, destination, content)


def github(
    task: Task,
    url: str,
    token: str,
    owner: str,
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
    Exposes some of the Github API functionality for operations on files
    in a Github repository.

    Example:

        nornir.run(files.github,
                   action="create",
                   url="https://github.localhost.com",
                   token="ABCD1234",
                   repository="test",
                   filename="config",
                   ref="master")

    Arguments:
        dry_run: Whether to apply changes or not
        url: Github instance URL
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
    session.headers.update({"Authorization": f"token {token}"})

    if commit_message == "":
        commit_message = "File created with nornir"

    if action == "create":
        diff = _create(
            task,
            session,
            url,
            owner,
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
            owner,
            repository,
            filename,
            content,
            branch,
            commit_message,
            dry_run,
        )
    elif action == "get":
        diff = _get(
            task, session, url, owner, repository, filename, destination, ref, dry_run
        )
    return Result(host=task.host, diff=diff, changed=bool(diff))
