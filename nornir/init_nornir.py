import pkg_resources
import warnings
from typing import Any, Dict, Optional, Type

from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.connections import Connections, ConnectionPlugin
from nornir.core.inventory import Inventory
from nornir.core.plugins.inventory import (
    InventoryPluginRegister,
    TransformFunctionRegister,
)
from nornir.core.state import GlobalState


def register_default_connection_plugins() -> None:
    discovered_plugins: Dict[str, Type[ConnectionPlugin]] = {
        entry_point.name: entry_point.load()
        for entry_point in pkg_resources.iter_entry_points("nornir.plugins.connections")
    }
    for k, v in discovered_plugins.items():
        Connections.register(k, v)


def load_inventory(config: Config,) -> Inventory:
    inventory_plugin = InventoryPluginRegister.get_plugin(config.inventory.plugin or "")
    inv = inventory_plugin(**config.inventory.options).load()

    if config.inventory.transform_function:
        transform_function = TransformFunctionRegister.get_plugin(
            config.inventory.transform_function
        )
        for h in inv.hosts.values():
            transform_function(h, **(config.inventory.transform_function_options or {}))

    return inv


def InitNornir(config_file: str = "", dry_run: bool = False, **kwargs: Any,) -> Nornir:
    """
    Arguments:
        config_file(str): Path to the configuration file (optional)
        dry_run(bool): Whether to simulate changes or not
        configure_logging: Whether to configure logging or not. This argument is being
            deprecated. Please use logging.enabled parameter in the configuration
            instead.
        **kwargs: Extra information to pass to the
            :obj:`nornir.core.configuration.Config` object

    Returns:
        :obj:`nornir.core.Nornir`: fully instantiated and configured
    """
    register_default_connection_plugins()

    if config_file:
        config = Config.from_file(config_file, **kwargs)
    else:
        config = Config.from_dict(**kwargs)

    data = GlobalState(dry_run=dry_run)

    config.logging.configure()

    return Nornir(inventory=load_inventory(config), config=config, data=data,)
