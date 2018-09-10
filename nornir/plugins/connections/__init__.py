from .napalm import Napalm
from .netmiko import Netmiko
from .paramiko import Paramiko
from nornir.core.connections import Connections


def register_default_connection_plugins() -> None:
    Connections.register(Napalm)
    Connections.register(Netmiko)
    Connections.register(Paramiko)
