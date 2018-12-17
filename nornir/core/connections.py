from abc import ABC, abstractmethod
from typing import Any, Dict, NoReturn, Optional, Type


from nornir.core.configuration import Config
from nornir.core.exceptions import (
    ConnectionPluginAlreadyRegistered,
    ConnectionPluginNotRegistered,
)


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
        extras: Optional[Dict[str, Any]] = None,
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
    available: Dict[str, Type[ConnectionPlugin]] = {}

    @classmethod
    def register(cls, name: str, plugin: Type[ConnectionPlugin]) -> None:
        """Registers a connection plugin with a specified name

        Args:
            name: name of the connection plugin to register
            plugin: defined connection plugin class

        Raises:
            :obj:`nornir.core.exceptions.ConnectionPluginAlreadyRegistered` if
                another plugin with the specified name was already registered
        """
        existing_plugin = cls.available.get(name)
        if existing_plugin is None:
            cls.available[name] = plugin
        elif existing_plugin != plugin:
            raise ConnectionPluginAlreadyRegistered(
                f"Connection plugin {plugin.__name__} can't be registered as "
                f"{name!r} because plugin {existing_plugin.__name__} "
                f"was already registered under this name"
            )

    @classmethod
    def deregister(cls, name: str) -> None:
        """Deregisters a registered connection plugin by its name

        Args:
            name: name of the connection plugin to deregister

        Raises:
            :obj:`nornir.core.exceptions.ConnectionPluginNotRegistered`
        """
        if name not in cls.available:
            raise ConnectionPluginNotRegistered(
                f"Connection {name!r} is not registered"
            )
        cls.available.pop(name)

    @classmethod
    def deregister_all(cls) -> None:
        """Deregisters all registered connection plugins"""
        cls.available = {}

    @classmethod
    def get_plugin(cls, name: str) -> Type[ConnectionPlugin]:
        """Fetches the connection plugin by name if already registered

        Args:
            name: name of the connection plugin

        Raises:
            :obj:`nornir.core.exceptions.ConnectionPluginNotRegistered`
        """
        if name not in cls.available:
            raise ConnectionPluginNotRegistered(
                f"Connection {name!r} is not registered"
            )
        return cls.available[name]
