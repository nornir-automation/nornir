import sys
from io import StringIO

from decorator import decorator


def wrap_cli_test(output, save_output=False):
    """
    This decorator captures the stdout and stder and compare it
    with the contects of the specified files.

    Arguments:
        output (string): Path to the output. stdout and stderr prefixes will be added automatically
        save_output (bool): Whether to save the output or not. Useful when creating the tests
    """

    @decorator
    def run_test(func, *args, **kwargs):

        stdout = StringIO()
        backup_stdout = sys.stdout
        sys.stdout = stdout

        stderr = StringIO()
        backup_stderr = sys.stderr
        sys.stderr = stderr

        func(*args, **kwargs)
        sys.stdout = backup_stdout
        sys.stderr = backup_stderr

        output_file = output

        if save_output:
            with open("{}.stdout".format(output_file), "w+") as f:
                f.write(stdout.getvalue())
            with open("{}.stderr".format(output_file), "w+") as f:
                f.write(stderr.getvalue())

        with open("{}.stdout".format(output_file), "r") as f:
            screen_output = stdout.getvalue()
            reference_output = f.read()
            assert screen_output == reference_output

        with open("{}.stderr".format(output_file), "r") as f:
            screen_output = stderr.getvalue()
            reference_output = f.read()
            assert screen_output == reference_output

    return run_test
