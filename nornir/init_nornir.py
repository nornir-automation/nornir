from typing import Any, Callable

from nornir.core import Nornir
from nornir.core.connections import Connections
from nornir.core.deserializer.configuration import Config
from nornir.core.state import GlobalState
from nornir.plugins.connections.napalm import Napalm
from nornir.plugins.connections.netmiko import Netmiko
from nornir.plugins.connections.paramiko import Paramiko


def register_default_connection_plugins() -> None:
    Connections.register("napalm", Napalm)
    Connections.register("netmiko", Netmiko)
    Connections.register("paramiko", Paramiko)


def cls_to_string(cls: Callable[..., Any]) -> str:
    return f"{cls.__module__}.{cls.__name__}"


def InitNornir(config_file="", dry_run=False, configure_logging=True, **kwargs):
    """
    Arguments:
        config_file(str): Path to the configuration file (optional)
        dry_run(bool): Whether to simulate changes or not
        **kwargs: Extra information to pass to the
            :obj:`nornir.core.configuration.Config` object

    Returns:
        :obj:`nornir.core.Nornir`: fully instantiated and configured
    """
    register_default_connection_plugins()

    if callable(kwargs.get("inventory", {}).get("plugin", "")):
        kwargs["inventory"]["plugin"] = cls_to_string(kwargs["inventory"]["plugin"])

    if callable(kwargs.get("inventory", {}).get("transform_function", "")):
        kwargs["inventory"]["transform_function"] = cls_to_string(
            kwargs["inventory"]["transform_function"]
        )

    conf = Config.load_from_file(config_file, **kwargs)

    data = GlobalState(dry_run=dry_run)

    if configure_logging:
        conf.logging.configure()

    inv = conf.inventory.plugin.deserialize(
        transform_function=conf.inventory.transform_function,
        config=conf,
        **conf.inventory.options,
    )

    return Nornir(inventory=inv, config=conf, data=data)
