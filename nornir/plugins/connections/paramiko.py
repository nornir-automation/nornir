import os
from typing import Dict

from nornir.core.connections import ConnectionPlugin

import paramiko


class Paramiko(ConnectionPlugin):
    """
    This plugin connects to the device with paramiko to the device and sets the
    relevant connection.

    Inventory:
        paramiko_options: maps to argument passed to ``ConnectHandler``.
        nornir_network_ssh_port: maps to ``port``
    """

    def _process_args(self) -> Dict:  # type: ignore
        connection_options = self.connection_options or {}
        parameters = {
            "hostname": self.hostname,
            "username": self.username,
            "password": self.password,
            "port": self.ssh_port,
        }
        connection_options.update(parameters)
        return connection_options

    def open(self) -> None:

        parameters = self._process_args()

        client = paramiko.SSHClient()
        client._policy = paramiko.WarningPolicy()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_config = paramiko.SSHConfig()
        ssh_config_file = self.configuration.ssh_config_file  # type: ignore
        if os.path.exists(ssh_config_file):
            with open(ssh_config_file) as f:
                ssh_config.parse(f)

        user_config = ssh_config.lookup(self.hostname)
        for k in ("hostname", "username", "port"):
            if k in user_config:
                parameters[k] = user_config[k]

        if "proxycommand" in user_config:
            parameters["sock"] = paramiko.ProxyCommand(user_config["proxycommand"])

        self.state["ssh_forward_agent"] = user_config.get("forwardagent") == "yes"

        # TODO configurable
        #  if ssh_key_file:
        #      parameters['key_filename'] = ssh_key_file
        if "identityfile" in user_config:
            parameters["key_filename"] = user_config["identityfile"]

        client.connect(**parameters)
        self.connection = client

    def close(self) -> None:
        self.connection.close()
