from typing import Any, Dict, Optional

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin


CONNECTION_NAME = "nornir_demo.demo"


class Demo(ConnectionPlugin):
    """
    This plugin is a demo plugin to show how to set up a new project
    """

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
