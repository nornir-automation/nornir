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
    RunnersPluginRegister.auto_register()
    runner_plugin = RunnersPluginRegister.get_plugin(config.runner.plugin)
    return runner_plugin(**config.runner.options)


def InitNornir(
    config_file: str = "",
    dry_run: bool = False,
    *,
    inventory: dict[str, Any] | None = None,
    ssh: dict[str, Any] | None = None,
    logging: dict[str, Any] | None = None,
    core: dict[str, Any] | None = None,
    runner: dict[str, Any] | None = None,
    user_defined: dict[str, Any] | None = None,
) -> Nornir:
    """Instantiate and configure a Nornir object.

    Arguments:
        config_file(str): Path to the configuration file (optional)
        dry_run(bool): Whether to simulate changes or not
        inventory(dict): Inventory configuration section
        ssh(dict): SSH configuration section
        logging(dict): Logging configuration section
        core(dict): Core configuration section
        runner(dict): Runner configuration section
        user_defined(dict): User-defined configuration section

    Returns:
        :obj:`nornir.core.Nornir`: fully instantiated and configured

    """
    ConnectionPluginRegister.auto_register()

    if config_file:
        config = Config.from_file(
            config_file,
            inventory=inventory,
            ssh=ssh,
            logging=logging,
            core=core,
            runner=runner,
            user_defined=user_defined,
        )
    else:
        config = Config.from_dict(
            inventory=inventory,
            ssh=ssh,
            logging=logging,
            core=core,
            runner=runner,
            user_defined=user_defined,
        )

    data = GlobalState(dry_run=dry_run)

    config.logging.configure()

    return Nornir(
        inventory=load_inventory(config),
        runner=load_runner(config),
        config=config,
        data=data,
    )
