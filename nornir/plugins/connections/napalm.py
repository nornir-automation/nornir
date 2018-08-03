from typing import Dict
from napalm import get_network_driver

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

    def _process_args(self) -> Dict:  # type: ignore
        connection_options = self.connection_options or {}
        if self.network_api_port:
            connection_options["port"] = self.network_api_port

        parameters = {
            "hostname": self.hostname,
            "username": self.username,
            "password": self.password,
            "optional_args": connection_options or {},
        }
        if connection_options.get("timeout"):
            parameters["timeout"] = connection_options.pop("timeout")
        return parameters

    def open(self) -> None:
        parameters = self._process_args()
        network_driver = get_network_driver(self.nos)
        connection = network_driver(**parameters)
        connection.open()
        self.connection = connection

    def close(self) -> None:
        self.connection.close()
