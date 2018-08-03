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

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        ssh_port: int,
        network_api_port: int,
        operating_system: str,
        nos: str,
        connection_options: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:

        self.hostname = hostname
        self.username = username
        self.password = password
        self.ssh_port = ssh_port
        self.network_api_port = network_api_port
        self.operating_system = operating_system
        self.nos = nos
        self.connection_options = connection_options
        self.configuration = configuration
        self.connection: Any = UnestablishedConnection()
        self.state: Dict[str, Any] = {}

    @abstractmethod
    def _process_args(self,) -> Dict:  # type: ignore
        """
        Process the connection objects bound to the object return a dictionary used to
        create the connection.
        """
        pass

    @abstractmethod
    def open(self,) -> None:
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
