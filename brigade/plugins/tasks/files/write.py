import difflib
import os

from brigade.core.task import Result


def _read_file(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        return f.read().splitlines()


def _generate_diff(filename, content, append):
    original = _read_file(filename)
    if append:
        c = list(original)
        c.extend(content.splitlines())
        content = c
    else:
        content = content.splitlines()

    diff = difflib.unified_diff(original, content, fromfile=filename, tofile="new")

    return "\n".join(diff)


def write(task, filename, content, append=False):
    """
    Write contents to a file (locally)

    Arguments:
        filename (``str``): file you want to write into
        conteint (``str``): content you want to write
        append (``bool``): whether you want to replace the contents or append to it

    Returns:
        * changed (``bool``):
        * diff (``str``): unified diff
    """
    diff = _generate_diff(filename, content, append)

    if not task.dry_run:
        mode = "a+" if append else "w+"
        with open(filename, mode=mode) as f:
            f.write(content)

    return Result(host=task.host, diff=diff, changed=bool(diff))
