import difflib
import os

from nornir.core.task import Result


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


def write_file(task, filename, content, append=False, dry_run=None):
    """
    Write contents to a file (locally)

    Arguments:
        dry_run (bool): Whether to apply changes or not
        filename (``str``): file you want to write into
        conteint (``str``): content you want to write
        append (``bool``): whether you want to replace the contents or append to it

    Returns:
        * changed (``bool``):
        * diff (``str``): unified diff
    """
    diff = _generate_diff(filename, content, append)

    if not task.is_dry_run(dry_run):
        mode = "a+" if append else "w+"
        with open(filename, mode=mode) as f:
            f.write(content)

    return Result(host=task.host, diff=diff, changed=bool(diff))
