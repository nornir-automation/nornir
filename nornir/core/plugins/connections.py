from typing import Any, Protocol

from nornir.core.configuration import Config
from nornir.core.plugins.register import PluginRegister

CONNECTIONS_PLUGIN_PATH = "nornir.plugins.connections"


class ConnectionPlugin(Protocol):
    def open(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
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


ConnectionPluginRegister: PluginRegister[type[ConnectionPlugin]] = PluginRegister(
    CONNECTIONS_PLUGIN_PATH
)
