from typing import Any, Dict, Optional

from napalm import get_network_driver

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin


class Napalm(ConnectionPlugin):
    """
    This plugin connects to the device using the NAPALM driver and sets the
    relevant connection.

    Inventory:
        napalm_options: maps directly to ``optional_args`` when establishing the connection
        nornir_network_api_port: maps to ``optional_args["port"]``
        napalm_options["timeout"]: maps to ``timeout``.
    """

    def open(
        self,
        hostname: str,
        username: str,
        password: str,
        port: int,
        platform: str,
        connection_options: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        connection_options = connection_options or {}
        if port:
            connection_options["port"] = port

        parameters = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "optional_args": connection_options or {},
        }
        if connection_options.get("timeout"):
            parameters["timeout"] = connection_options["timeout"]

        network_driver = get_network_driver(platform)
        connection = network_driver(**parameters)
        connection.open()
        self.connection = connection

    def close(self) -> None:
        self.connection.close()
