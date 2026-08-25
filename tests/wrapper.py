import pathlib
import sys
from collections.abc import Callable
from io import StringIO
from typing import Any

from decorator import decorator


def wrap_cli_test(output: str, save_output: bool = False) -> Callable[[Callable[..., Any]], None]:
    """Capture the stdout and stderr and compare them with the contents of the given files.

    Arguments:
        output (string): Path to the output. stdout and stderr prefixes will be added automatically
        save_output (bool): Whether to save the output or not. Useful when creating the tests

    Returns:
        A decorator that wraps the test function.

    """

    @decorator
    def run_test(func: Callable[..., Any], *args: Any, **kwargs: dict[str, Any]) -> Any:
        stdout = StringIO()
        backup_stdout = sys.stdout
        sys.stdout = stdout

        stderr = StringIO()
        backup_stderr = sys.stderr
        sys.stderr = stderr

        func(*args, **kwargs)
        sys.stdout = backup_stdout
        sys.stderr = backup_stderr

        stdout_file = pathlib.Path(f"{output}.stdout")
        stderr_file = pathlib.Path(f"{output}.stderr")

        if save_output:
            stdout_file.write_text(stdout.getvalue(), encoding="utf-8")
            stderr_file.write_text(stderr.getvalue(), encoding="utf-8")

        assert stdout.getvalue() == stdout_file.read_text(encoding="utf-8")
        assert stderr.getvalue() == stderr_file.read_text(encoding="utf-8")

    return run_test
