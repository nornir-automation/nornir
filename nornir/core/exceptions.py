from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from nornir.core.connection import Connection
    from nornir.core.result import AggregatedResult, MultiResult, Result  # noqa
    from nornir.core.tasks import Task


class ConnectionException(Exception):
    """
    Superclass for all the Connection* Exceptions
    """

    def __init__(self, connection: "Connection") -> None:
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


class PluginAlreadyRegistered(Exception):
    """
    Raised when trying to register an already registered plugin
    """

    pass


class PluginNotRegistered(Exception):
    """
    Raised when trying to access a plugin that is not registered
    """

    pass


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


class NornirNoValidInventoryError(Exception):
    """
    Raised by nornir when :meth:`nornir.plugins.inventory.parse` fails to load any valid inventory
    """

    pass


class ConflictingConfigurationWarning(UserWarning):
    pass
