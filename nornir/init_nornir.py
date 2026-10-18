from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.exceptions import (
    InventoryPluginAmbiguousError,
    InventoryPluginContractError,
    InventoryPluginNotSyncError,
    TransformFunctionAmbiguousError,
    TransformFunctionNotSyncError,
)
from nornir.core.inventory import Inventory, TransformFunction
from nornir.core.plugins.connections import (
    CapabilityConnectionPluginRegister,
    ConnectionPluginRegister,
)
from nornir.core.plugins.inventory import (
    AsyncTransformFunction,
    AsyncTransformFunctionRegister,
    CapabilityInventoryPlugin,
    CapabilityInventoryPluginRegister,
    InventoryPlugin,
    InventoryPluginRegister,
    TransformFunctionRegister,
    _is_async_capability_inventory_plugin,
    _is_sync_capability_inventory_plugin,
    _validate_capability_inventory_plugin,
)
from nornir.core.plugins.runners import RunnerPlugin, RunnersPluginRegister
from nornir.core.state import GlobalState

if TYPE_CHECKING:
    from collections.abc import Callable


def load_inventory(
    config: Config,
) -> Inventory:
    """Build the inventory the configuration asks for.

    The inventory plugin named in ``config.inventory.plugin`` is instantiated with
    ``config.inventory.options`` and asked to load. When a transform function is
    configured it is then applied to every host in turn.

    The name is looked up in both the legacy and the capability-aware inventory
    registries. A capability-aware plugin must declare synchronous support.

    Arguments:
        config: Configuration to read the inventory settings from

    Returns:
        :obj:`nornir.core.inventory.Inventory`: The loaded inventory.

    Raises:
        nornir.core.exceptions.PluginNotRegistered: no plugin is registered under the
            configured name
        nornir.core.exceptions.InventoryPluginAmbiguousError: the name is registered in
            both inventory registries
        nornir.core.exceptions.InventoryPluginContractError: a capability-aware plugin
            violates its contract
        nornir.core.exceptions.InventoryPluginNotSyncError: the plugin only declares
            asyncio support; use :func:`AInitNornir`
        nornir.core.exceptions.TransformFunctionAmbiguousError: the transform function
            name is registered in both transform function registries
        nornir.core.exceptions.TransformFunctionNotSyncError: the transform function is
            defined with ``async def``; use :func:`AInitNornir`

    """
    plugin_name = config.inventory.plugin
    source = _resolve_inventory_plugin(plugin_name)
    transform = _resolve_transform_function(config)
    if transform is not None and transform.is_async:
        raise TransformFunctionNotSyncError(transform.name)

    if isinstance(source, _LegacyInventorySource):
        inv = source.plugin_class(**config.inventory.options).load()
    else:
        plugin = source.plugin_class(**config.inventory.options)
        capabilities = _validate_capability_inventory_plugin(plugin_name, plugin)
        if "sync" not in capabilities:
            raise InventoryPluginNotSyncError(plugin_name)
        if not _is_sync_capability_inventory_plugin(plugin):
            raise InventoryPluginContractError(
                plugin_name, "validated synchronous load is no longer available"
            )
        inv = plugin.load()

    if transform is not None:
        _transform_hosts(inv, transform.function, config)

    return inv


async def aload_inventory(
    config: Config,
) -> Inventory:
    """Build the inventory the configuration asks for, without blocking the event loop.

    Asynchronous counterpart of :func:`load_inventory`. A plugin that declares asyncio
    support is loaded by awaiting its ``aload``. Any other plugin, including every
    legacy plugin, is loaded in a worker thread. A synchronous transform function also
    runs in a worker thread; a transform function defined with ``async def`` is awaited
    once per host, in inventory order, one host at a time. The running event loop keeps
    serving other work, and no event loop is created.

    Arguments:
        config: Configuration to read the inventory settings from

    Returns:
        :obj:`nornir.core.inventory.Inventory`: The loaded inventory.

    Raises:
        nornir.core.exceptions.PluginNotRegistered: no plugin is registered under the
            configured name
        nornir.core.exceptions.InventoryPluginAmbiguousError: the name is registered in
            both inventory registries
        nornir.core.exceptions.InventoryPluginContractError: a capability-aware plugin
            violates its contract
        nornir.core.exceptions.TransformFunctionAmbiguousError: the transform function
            name is registered in both transform function registries

    """
    plugin_name = config.inventory.plugin
    source = _resolve_inventory_plugin(plugin_name)
    transform = _resolve_transform_function(config)
    sync_transform = transform.function if transform and not transform.is_async else None

    if isinstance(source, _LegacyInventorySource):
        # Legacy plugins were never asked to keep their constructor free of I/O, so
        # they are constructed in the worker thread as well.
        legacy_class = source.plugin_class
        inv = await asyncio.to_thread(
            _load_and_transform,
            lambda: legacy_class(**config.inventory.options).load(),
            sync_transform,
            config,
        )
    else:
        plugin = source.plugin_class(**config.inventory.options)
        capabilities = _validate_capability_inventory_plugin(plugin_name, plugin)
        if "asyncio" in capabilities:
            if not _is_async_capability_inventory_plugin(plugin):
                raise InventoryPluginContractError(
                    plugin_name, "validated asyncio aload is no longer available"
                )
            inv = await plugin.aload()
            if sync_transform is not None:
                await asyncio.to_thread(_transform_hosts, inv, sync_transform, config)
        else:
            if not _is_sync_capability_inventory_plugin(plugin):
                raise InventoryPluginContractError(
                    plugin_name, "validated synchronous load is no longer available"
                )
            inv = await asyncio.to_thread(_load_and_transform, plugin.load, sync_transform, config)

    if transform is not None and transform.is_async:
        for h in inv.hosts.values():
            await transform.function(h, **(config.inventory.transform_function_options or {}))

    return inv


@dataclass(frozen=True)
class _LegacyInventorySource:
    plugin_class: type[InventoryPlugin]


@dataclass(frozen=True)
class _CapabilityInventorySource:
    plugin_class: type[CapabilityInventoryPlugin]


def _resolve_inventory_plugin(
    plugin_name: str,
) -> _LegacyInventorySource | _CapabilityInventorySource:
    InventoryPluginRegister.auto_register()
    CapabilityInventoryPluginRegister.auto_register()

    capability_class = CapabilityInventoryPluginRegister.available.get(plugin_name)
    if capability_class is None:
        return _LegacyInventorySource(InventoryPluginRegister.get_plugin(plugin_name))
    if plugin_name in InventoryPluginRegister.available:
        raise InventoryPluginAmbiguousError(plugin_name)
    return _CapabilityInventorySource(capability_class)


@dataclass(frozen=True)
class _ResolvedTransformFunction:
    name: str
    function: Callable[..., Any]
    is_async: bool


def _resolve_transform_function(config: Config) -> _ResolvedTransformFunction | None:
    name = config.inventory.transform_function
    if not name:
        return None
    TransformFunctionRegister.auto_register()
    AsyncTransformFunctionRegister.auto_register()

    function: TransformFunction | AsyncTransformFunction | None = (
        AsyncTransformFunctionRegister.available.get(name)
    )
    if function is None:
        function = TransformFunctionRegister.get_plugin(name)
    elif name in TransformFunctionRegister.available:
        raise TransformFunctionAmbiguousError(name)
    # Dispatch follows how the function is defined, not where it was registered.
    return _ResolvedTransformFunction(name, function, inspect.iscoroutinefunction(function))


def _transform_hosts(
    inv: Inventory, transform_function: Callable[..., None], config: Config
) -> None:
    for h in inv.hosts.values():
        transform_function(h, **(config.inventory.transform_function_options or {}))


def _load_and_transform(
    load: Callable[[], Inventory],
    transform_function: Callable[..., None] | None,
    config: Config,
) -> Inventory:
    inv = load()
    if transform_function is not None:
        _transform_hosts(inv, transform_function, config)
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


def _prepare(
    config_file: str,
    dry_run: bool,
    *,
    inventory: dict[str, Any] | None,
    ssh: dict[str, Any] | None,
    logging: dict[str, Any] | None,
    core: dict[str, Any] | None,
    runner: dict[str, Any] | None,
    user_defined: dict[str, Any] | None,
) -> tuple[Config, GlobalState]:
    """Build the configuration and global state shared by InitNornir and AInitNornir.

    Registers the installed connection plugins, reads the configuration and configures
    logging, so that the two entry points only differ in how the inventory is loaded.

    Returns:
        The configuration and the global state for the new Nornir object.

    """
    ConnectionPluginRegister.auto_register()
    CapabilityConnectionPluginRegister.auto_register()

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

    return config, data


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
    config, data = _prepare(
        config_file,
        dry_run,
        inventory=inventory,
        ssh=ssh,
        logging=logging,
        core=core,
        runner=runner,
        user_defined=user_defined,
    )

    return Nornir(
        inventory=load_inventory(config),
        runner=load_runner(config),
        config=config,
        data=data,
    )


async def AInitNornir(
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
    """Instantiate and configure a Nornir object from a running event loop.

    Asynchronous counterpart of :func:`InitNornir`, with the same arguments and the
    same result. Only the inventory is loaded differently: see :func:`aload_inventory`.
    Use it as ``nr = await AInitNornir(...)``.

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
    config, data = _prepare(
        config_file,
        dry_run,
        inventory=inventory,
        ssh=ssh,
        logging=logging,
        core=core,
        runner=runner,
        user_defined=user_defined,
    )

    return Nornir(
        inventory=await aload_inventory(config),
        runner=load_runner(config),
        config=config,
        data=data,
    )
