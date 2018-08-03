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

    def open(self) -> None:
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
        self.connection = ConnectHandler(**netmiko_connection_args)

    def close(self) -> None:
        self.connection.disconnect()
