from pathlib import Path
from typing import Any, Dict, Optional

from ncclient import manager

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin


class Netconf(ConnectionPlugin):
    """
    This plugin connects to the device via NETCONF using ncclient library.

    Inventory:
        extras: See
        `here <https://ncclient.readthedocs.io/en/latest/transport.html#ncclient.transport.SSHSession.connect>`_

    Example on how to configure a device to use netconfig without using an ssh agent and without verifying the keys::

        ---
        nc_device:
            hostname: 192.168.16.20
            username: admin
            password: admin
            port: 2022
            connection_options:
                netconf:
                    extras:
                        allow_agent: False
                        hostkey_verify: False

    Then it can be used like::

        >>> from nornir import InitNornir
        >>> from nornir.core.task import Result, Task
        >>>
        >>> nr = InitNornir(
        >>>    inventory={
        >>>        "options": {
        >>>            "hosts": {
        >>>                "rtr00": {
        >>>                    "hostname": "localhost",
        >>>                   "username": "admin",
        >>>                    "password": "admin",
        >>>                    "port": 65030,
        >>>                    "platform": "whatever",
        >>>                    "connection_options": {
        >>>                        "netconf": {"extras": {"hostkey_verify": False}}
        >>>                    },
        >>>                }
        >>>           }
        >>>        }
        >>>    }
        >>>)
        >>>
        >>>
        >>> def netconf_code(task: Task) -> Result:
        >>>    manager = task.host.get_connection("netconf", task.nornir.config)
        >>>
        >>>    # get running config and system state
        >>>    print(manager.get())
        >>>
        >>>    # get only hostname
        >>>    print(manager.get(filter=("xpath", "/sys:system/sys:hostname")))
        >>>
        >>>    # get candidate config
        >>>    print(manager.get_config("candidate"))
        >>>
        >>>    # lock
        >>>    print(manager.lock("candidate"))
        >>>
        >>>    # edit configuration
        >>>    res = manager.edit_config(
        >>>        "candidate",
        >>>        "<sys:system><sys:hostname>asd</sys:hostname></sys:system>",
        >>>        default_operation="merge",
        >>>    )
        >>>    print(res)
        >>>
        >>>    print(manager.commit())
        >>>
        >>>    # unlock
        >>>    print(manager.unlock("candidate"))
        >>>
        >>>    return Result(result="ok", host=task.host)
        >>>
        >>>
        >>> nr.run(task=netconf_code)
    """  # noqa

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
            "port": port or 830,
        }

        if "ssh_config" not in extras:
            try:
                ssh_config_file = Path(configuration.ssh.config_file)  # type: ignore
                if ssh_config_file.exists():
                    parameters["ssh_config"] = ssh_config_file
            except AttributeError:
                pass

        parameters.update(extras)

        connection = manager.connect_ssh(**parameters)
        self.connection = connection

    def close(self) -> None:
        self.connection.close_session()
