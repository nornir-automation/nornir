from typing import Dict

from netmiko import ConnectHandler
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
    def _process_args(self) -> Dict:    # type: ignore
        """
        Process the connection objects bound to the object return a dictionary used to
        create the connection.
        """
        parameters = {
            "host": self.hostname,
            "username": self.username,
            "password": self.password,
            "port": self.ssh_port,
        }

        nos = self.nos
        if nos is not None:
            # Look device_type up in corresponding map, if no entry return the host.nos unmodified
            device_type = napalm_to_netmiko_map.get(nos, nos)
            parameters["device_type"] = device_type

        netmiko_connection_args = self.connection_options or {}
        netmiko_connection_args.update(parameters)
        return parameters

    def open(self) -> None:
        parameters = self._process_args()
        self.connection = ConnectHandler(**parameters)

    def close(self) -> None:
        self.connection.disconnect()
