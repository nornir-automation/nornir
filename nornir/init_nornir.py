from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.state import GlobalState
from nornir.core.connections import Connections

from nornir.plugins.connections.napalm import Napalm
from nornir.plugins.connections.netmiko import Netmiko
from nornir.plugins.connections.paramiko import Paramiko


def register_default_connection_plugins() -> None:
    Connections.register("napalm", Napalm)
    Connections.register("netmiko", Netmiko)
    Connections.register("paramiko", Paramiko)


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

    conf = Config(path=config_file, **kwargs)
    GlobalState.dry_run = dry_run

    if configure_logging:
        conf.logging.configure()

    inv_class = conf.inventory.get_plugin()
    transform_function = conf.inventory.get_transform_function()
    inv = inv_class.deserialize(
        transform_function=transform_function, config=conf, **conf.inventory.options
    )

    return Nornir(inventory=inv, _config=conf)
