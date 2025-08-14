from typing import Any, Dict, Optional, Protocol, Type

from nornir.core.configuration import Config
from nornir.core.plugins.register import PluginRegister

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

    def close(self) -> None:
        """Close the connection with the device"""

    @property
    def connection(self) -> Any:
        """
        Established connection
        """


ConnectionPluginRegister: PluginRegister[Type[ConnectionPlugin]] = PluginRegister(
    CONNECTIONS_PLUGIN_PATH
)
