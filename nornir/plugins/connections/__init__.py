from .napalm import Napalm
from .netmiko import Netmiko
from .paramiko import Paramiko
from nornir.core.connections import Connections


def register_default_connection_plugins() -> None:
    Connections.register("napalm", Napalm)
    Connections.register("netmiko", Netmiko)
    Connections.register("paramiko", Paramiko)
