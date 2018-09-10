from typing import Any, Dict, Optional

from napalm import get_network_driver

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin


class Napalm(ConnectionPlugin):
    """
    This plugin connects to the device using the NAPALM driver and sets the
    relevant connection.

    Inventory:
        connection_options: passed as it is to the napalm driver
    """

    default_conn_name = "napalm"

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        connection_options: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        connection_options = connection_options or {}

        parameters: Dict[str, Any] = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "optional_args": {},
        }
        parameters.update(connection_options)

        if port and "port" not in parameters["optional_args"]:
            parameters["optional_args"]["port"] = port

        network_driver = get_network_driver(platform)
        connection = network_driver(**parameters)
        connection.open()
        self.connection = connection

    def close(self) -> None:
        self.connection.close()
