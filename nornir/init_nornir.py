from __future__ import annotations

from typing import Any

from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.inventory import Inventory
from nornir.core.plugins.connections import ConnectionPluginRegister
from nornir.core.plugins.inventory import (
    InventoryPluginRegister,
    TransformFunctionRegister,
)
from nornir.core.plugins.runners import RunnerPlugin, RunnersPluginRegister
from nornir.core.state import GlobalState


def load_inventory(
    config: Config,
) -> Inventory:
    """Build the inventory the configuration asks for.

    The inventory plugin named in ``config.inventory.plugin`` is instantiated with
    ``config.inventory.options`` and asked to load. When a transform function is
    configured it is then applied to every host in turn.

    Arguments:
        config: Configuration to read the inventory settings from

    Returns:
        :obj:`nornir.core.inventory.Inventory`: The loaded inventory.

    Raises:
        nornir.core.exceptions.PluginNotRegistered: no plugin is registered under the
            configured name

    """
    InventoryPluginRegister.auto_register()
    inventory_plugin = InventoryPluginRegister.get_plugin(config.inventory.plugin)
    inv = inventory_plugin(**config.inventory.options).load()

    if config.inventory.transform_function:
        TransformFunctionRegister.auto_register()
        transform_function = TransformFunctionRegister.get_plugin(
            config.inventory.transform_function
        )
        for h in inv.hosts.values():
            transform_function(h, **(config.inventory.transform_function_options or {}))

    return inv


def load_runner(
    config: Config,
) -> RunnerPlugin:
    """Build the runner the configuration asks for.

    Arguments:
        config: Configuration to read the runner settings from

    Returns:
        :obj:`nornir.core.plugins.runners.RunnerPlugin`: The plugin named in
        ``config.runner.plugin``, instantiated with ``config.runner.options``.

    Raises:
        nornir.core.exceptions.PluginNotRegistered: no plugin is registered under the
            configured name

    """
    RunnersPluginRegister.auto_register()
    runner_plugin = RunnersPluginRegister.get_plugin(config.runner.plugin)
    return runner_plugin(**config.runner.options)


def InitNornir(
    config_file: str = "",
    dry_run: bool = False,
    **kwargs: Any,
) -> Nornir:
    """Instantiate and configure a Nornir object.

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
    ConnectionPluginRegister.auto_register()

    config = Config.from_file(config_file, **kwargs) if config_file else Config.from_dict(**kwargs)

    data = GlobalState(dry_run=dry_run)

    config.logging.configure()

    return Nornir(
        inventory=load_inventory(config),
        runner=load_runner(config),
        config=config,
        data=data,
    )
