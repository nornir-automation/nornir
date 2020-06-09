from typing import Any, Dict, Type, Optional

from nornir.core.configuration import Config
from nornir.core.plugins.register import PluginRegister

from typing_extensions import Protocol


CONNECTIONS_PLUGIN_PATH = "nornir.plugins.connections"


class ConnectionPlugin(Protocol):
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

    def close(self) -> None:
        """Close the connection with the device"""
        pass

    @property
    def connection(self) -> Any:
        """
        Established connection
        """
        pass


ConnectionPluginRegister: PluginRegister[Type[ConnectionPlugin]] = PluginRegister(
    CONNECTIONS_PLUGIN_PATH
)
