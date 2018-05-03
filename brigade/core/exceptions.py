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

    @property
    def failed_hosts(self):
        return {k: v for k, v in self.result.items() if v.failed}

    def __str__(self):
        text = "\n"
        for k, r in self.result.items():
            text += "{}\n".format("#" * 40)
            if r.failed:
                text += "# {} (failed)\n".format(k)
            else:
                text += "# {} (succeeded)\n".format(k)
            text += "{}\n".format("#" * 40)
            for sub_r in r:
                text += "**** {}\n".format(sub_r.name)
                text += "{}\n".format(sub_r)
        return text


class BrigadeSubTaskError(Exception):
    """
    Raised by brigade when a sub task managed by :meth:`brigade.core.Task.run`
    has failed

    Arguments:
        task (:obj:`brigade.core.task.Task`): The subtask that failed
        result (:obj:`brigade.core.task.Result`): The result of the failed task
    Attributes:
        task (:obj:`brigade.core.task.Task`): The subtask that failed
        result (:obj:`brigade.core.task.Result`): The result of the failed task
    """

    def __init__(self, task, result):
        self.task = task
        self.result = result

    def __str__(self):
        return "Subtask: {} (failed)\n".format(self.task)
