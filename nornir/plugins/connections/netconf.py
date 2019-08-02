from typing import Any, Dict, Optional

from ncclient import manager

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin


class Netconf(ConnectionPlugin):
    """
    This plugin connects to the device via NETCONF using ncclient library.

    Inventory:
        extras: See https://ncclient.readthedocs.io/en/latest/transport.html#ncclient.transport.SSHSession.connect  # noqa
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
        extras = extras or {}

        parameters: Dict[str, Any] = {
            "host": hostname,
            "username": username,
            "password": password,
            "port": port,
        }

        if "ssh_config" not in extras:
            try:
                parameters["ssh_config"] = configuration.ssh.config_file  # type: ignore
            except AttributeError:
                pass

        parameters.update(extras)
        parameters["ssh_config"] = None

        connection = manager.connect_ssh(**parameters)
        self.connection = connection

    def close(self) -> None:
        self.connection.close_session()
