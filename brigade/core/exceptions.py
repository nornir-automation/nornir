from builtins import super


class CommandError(Exception):
    """
    Raised when there is a command error.

    Attributes:
        status_code (int): status code returned by the command
        stdout (str): stdout
        stderr (str): stderr
        command (str): command that triggered the error
    """

    def __init__(self, command, status_code, stdout, stderr):
        self.status_code = status_code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
        super().__init__(command, status_code, stdout, stderr)


class FileError(Exception):
    """
    Raised when there is a file error.

    Attributes:
        file (str): file that triggered the error
        error (str): the error message
    """

    def __init__(self, file, error):
        self.file = file
        self.error = error
        super().__init__(file, error)


class TemplateError(Exception):

    def __init__(self, message, lineno, name=None, filename=None):
        self.message = message
        self.lineno = lineno
        self.name = name
        self.filename = filename
        super().__init__(message, lineno, name, filename)


class BrigadeExecutionError(Exception):
    """
    Raised by brigade when any of the tasks managed by :meth:`brigade.core.Brigade.run`
    when any of the tasks fail.

    Arguments:
        result (:obj:`brigade.core.task.AggregatedResult`):
    Attributes:
        result (:obj:`brigade.core.task.AggregatedResult`):
    """
    def __init__(self, result):
        self.result = result
        self.failed_hosts = result.failed_hosts
        self.tracebacks = result.tracebacks

    def __str__(self):
        text = "\n"
        for k, r in self.result.items():
            text += "{}\n".format("#" * 40)
            text += "# {} (succeeded) \n".format(k)
            text += "{}\n".format("#" * 40)
            text += "{}\n".format(r)
        for k, r in self.tracebacks.items():
            text += "{}\n".format("#" * 40)
            text += "# {} (failed) \n".format(k)
            text += "{}\n".format("#" * 40)
            text += "{}\n".format(r)
        return text
