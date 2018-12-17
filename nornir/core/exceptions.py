class ConnectionException(Exception):
    """
    Superclass for all the Connection* Exceptions
    """

    def __init__(self, connection):
        self.connection = connection


class ConnectionAlreadyOpen(ConnectionException):
    """
    Raised when opening an already opened connection
    """

    pass


class ConnectionNotOpen(ConnectionException):
    """
    Raised when trying to close a connection that isn't open
    """

    pass


class ConnectionPluginAlreadyRegistered(ConnectionException):
    """
    Raised when trying to register an already registered plugin
    """

    pass


class ConnectionPluginNotRegistered(ConnectionException):
    """
    Raised when trying to access a plugin that is not registered
    """

    pass


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


class NornirExecutionError(Exception):
    """
    Raised by nornir when any of the tasks managed by :meth:`nornir.core.Nornir.run`
    when any of the tasks fail.

    Arguments:
        result (:obj:`nornir.core.task.AggregatedResult`):
    Attributes:
        result (:obj:`nornir.core.task.AggregatedResult`):
    """

    def __init__(self, result):
        self.result = result

    @property
    def failed_hosts(self):
        """
        Hosts that failed to complete the task
        """
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


class NornirSubTaskError(Exception):
    """
    Raised by nornir when a sub task managed by :meth:`nornir.core.Task.run`
    has failed

    Arguments:
        task (:obj:`nornir.core.task.Task`): The subtask that failed
        result (:obj:`nornir.core.task.Result`): The result of the failed task
    Attributes:
        task (:obj:`nornir.core.task.Task`): The subtask that failed
        result (:obj:`nornir.core.task.Result`): The result of the failed task
    """

    def __init__(self, task, result):
        self.task = task
        self.result = result

    def __str__(self):
        return "Subtask: {} (failed)\n".format(self.task)
