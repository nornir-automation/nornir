from typing import Any

import asyncio

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
    return asyncio.run(load_inventory_async(config=config))


async def load_inventory_async(
    config: Config,
) -> Inventory:
    InventoryPluginRegister.auto_register()
    inventory_plugin = InventoryPluginRegister.get_plugin(config.inventory.plugin)
    inventory = inventory_plugin(**config.inventory.options)
    if asyncio.iscoroutinefunction(inventory.load):
        inv = await inventory.load()
    else:
        inv = inventory.load()

    if config.inventory.transform_function:
        TransformFunctionRegister.auto_register()
        transform_function = TransformFunctionRegister.get_plugin(
            config.inventory.transform_function
        )

        if asyncio.iscoroutinefunction(transform_function):
            for h in inv.hosts.values():
                await transform_function(
                    h, **(config.inventory.transform_function_options or {})
                )
        else:
            for h in inv.hosts.values():
                transform_function(
                    h, **(config.inventory.transform_function_options or {})
                )

    return inv


def load_runner(
    config: Config,
) -> RunnerPlugin:
    RunnersPluginRegister.auto_register()
    runner_plugin = RunnersPluginRegister.get_plugin(config.runner.plugin)
    return runner_plugin(**config.runner.options)


async def InitNornirAsync(
    config_file: str = "",
    dry_run: bool = False,
    **kwargs: Any,
) -> Nornir:
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
    ConnectionPluginRegister.auto_register()

    if config_file:
        config = Config.from_file(config_file, **kwargs)
    else:
        config = Config.from_dict(**kwargs)

    data = GlobalState(dry_run=dry_run)

    config.logging.configure()

    return Nornir(
        inventory=await load_inventory_async(config),
        runner=load_runner(config),
        config=config,
        data=data,
    )


def InitNornir(
    config_file: str = "",
    dry_run: bool = False,
    **kwargs: Any,
) -> Nornir:
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
    return asyncio.run(
        InitNornirAsync(config_file=config_file, dry_run=dry_run, **kwargs)
    )
