class CommandError(Exception):
    """
    Raised when there is a command error.

    Attributes:
        status_code (int): status code returned by the command
        stdout (str): stdout
        stderr (str): stderr
        command (str): command that triggered the error
    """

    def __init__(self, message, command, status_code, stdout, stderr):
        self.status_code = status_code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command


class BrigadeExecutionException(Exception):
    """
    Raised by brigade when any of the tasks managed by :meth:`brigade.core.Brigade.run`
    when any of the tasks fail.

    Attributes:
        result (dict): A dictionary with the results for each individual execution.
          The hosts that raised an exception will contain the resulting exection.
        failed (list): List of hosts that failed.
    """

    def __init__(self, result):
        self.result = result
        self.failed = [h for h, r in result.items() if isinstance(r, Exception)]
