from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from nornir.core.inventory import Host
    from nornir.core.task import (  # noqa: W0611
        AggregatedResult,
        MultiResult,
        Result,
        Task,
    )


class ConnectionException(Exception):
    """
    Superclass for all the Connection* Exceptions
    """

    def __init__(self, host: "Host", name: str, details: str = "") -> None:
        if not details:
            msg = f"Host {host.name!r}: problem with connection {name!r}"
        else:
            msg = f"Host {host.name!r}: connection {name!r} {details}"
        super().__init__(msg)
        self.conn_name = name
        self.host = host


class ConnectionAlreadyOpen(ConnectionException):
    """
    Raised when opening an already opened connection
    """

    def __init__(
        self,
        host: "Host",
        name: str,
        details: str = "trying to open connection which is already open",
    ) -> None:
        super().__init__(host, name, details)


class ConnectionNotOpen(ConnectionException):
    """
    Raised when the connection is supposed to be open but it isn't
    """

    def __init__(self, host: "Host", name: str, details: str = "is not open") -> None:
        super().__init__(host, name, details)


class ConnectionPluginException(Exception):
    pass


class ConnectionPluginAlreadyRegistered(ConnectionPluginException):
    """
    Raised when trying to register an already registered plugin
    """

    pass


class ConnectionPluginNotRegistered(ConnectionPluginException):
    """
    Raised when trying to access a plugin that is not registered
    """

    pass


class CommandError(Exception):
    """
    Raised when there is a command error.
    """

    def __init__(
        self, command: str, status_code: int, stdout: str, stderr: str
    ) -> None:
        self.status_code = status_code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
        super().__init__(command, status_code, stdout, stderr)


class NornirExecutionError(Exception):
    """
    Raised by nornir when any of the tasks managed by :meth:`nornir.core.Nornir.run`
    when any of the tasks fail.
    """

    def __init__(self, result: "AggregatedResult") -> None:
        self.result = result

    @property
    def failed_hosts(self) -> Dict[str, "MultiResult"]:
        """
        Hosts that failed to complete the task
        """
        return {k: v for k, v in self.result.items() if v.failed}

    def __str__(self) -> str:
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
    Raised by nornir when a sub task managed by :meth:`nornir.core.Task.run` has failed
    """

    def __init__(self, task: "Task", result: "Result"):
        self.task = task
        self.result = result

    def __str__(self) -> str:
        return "Subtask: {} (failed)\n".format(self.task)


class ConflictingConfigurationWarning(UserWarning):
    pass
