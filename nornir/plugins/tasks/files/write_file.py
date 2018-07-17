import difflib
import os
from typing import List, Optional

from nornir.core.task import Result, Task


def _read_file(file: str) -> List[str]:
    if not os.path.exists(file):
        return []

    with open(file, "r") as f:
        return f.read().splitlines()


def _generate_diff(filename: str, content: str, append: bool) -> str:
    original = _read_file(filename)
    if append:
        c = list(original)
        c.extend(content.splitlines())
        new_content = c
    else:
        new_content = content.splitlines()

    diff = difflib.unified_diff(original, new_content, fromfile=filename, tofile="new")

    return "\n".join(diff)


def write_file(
    task: Task,
    filename: str,
    content: str,
    append: bool = False,
    dry_run: Optional[bool] = None,
) -> Result:
    """
    Write contents to a file (locally)

    Arguments:
        dry_run: Whether to apply changes or not
        filename: file you want to write into
        content: content you want to write
        append: whether you want to replace the contents or append to it

    Returns:
        Result object with the following attributes set:
          * changed (``bool``):
          * diff (``str``): unified diff
    """
    diff = _generate_diff(filename, content, append)

    if not task.is_dry_run(dry_run):
        mode = "a+" if append else "w+"
        with open(filename, mode=mode) as f:
            f.write(content)

    return Result(host=task.host, diff=diff, changed=bool(diff))
