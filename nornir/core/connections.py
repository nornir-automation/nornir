from abc import ABC, abstractmethod
from typing import Any, Dict, NoReturn, Optional


from nornir.core.configuration import Config


class ConnectionPlugin(ABC):
    """
    Connection plugins have to inherit from this class and provide implementations
    for both the :meth:`open` and :meth:`close` methods.

    Attributes:
        connection: Underlying connection. Populated by :meth:`open`.
        state: Dictionary to hold any data that needs to be shared between
            the connection plugin and the plugin tasks using this connection.
    """

    __slots__ = ("connection", "state")

    def __init__(self) -> None:
        self.connection: Any = UnestablishedConnection()
        self.state: Dict[str, Any] = {}

    @abstractmethod
    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        advanced_options: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        """
        Connect to the device and populate the attribute :attr:`connection` with
        the underlying connection
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the connection with the device"""
        pass


class UnestablishedConnection(object):
    def close(self) -> NoReturn:
        raise ValueError("Connection not established")

    disconnect = close


class Connections(Dict[str, ConnectionPlugin]):
    pass
