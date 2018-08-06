from typing import Any, Dict, Optional

from netmiko import ConnectHandler

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin

napalm_to_netmiko_map = {
    "ios": "cisco_ios",
    "nxos": "cisco_nxos",
    "eos": "arista_eos",
    "junos": "juniper_junos",
    "iosxr": "cisco_xr",
}


class Netmiko(ConnectionPlugin):
    """
    This plugin connects to the device using the NAPALM driver and sets the
    relevant connection.

    Inventory:
        netmiko_options: maps to argument passed to ``ConnectHandler``.
        nornir_network_ssh_port: maps to ``port``
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
        parameters = {
            "host": hostname,
            "username": username,
            "password": password,
            "port": port,
        }

        if platform is not None:
            # Look platform up in corresponding map, if no entry return the host.nos unmodified
            platform = napalm_to_netmiko_map.get(platform, platform)
            parameters["device_type"] = platform

        netmiko_connection_args = connection_options or {}
        netmiko_connection_args.update(parameters)
        self.connection = ConnectHandler(**netmiko_connection_args)

    def close(self) -> None:
        self.connection.disconnect()
