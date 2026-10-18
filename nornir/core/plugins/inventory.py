from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeGuard

from nornir.core.exceptions import InventoryPluginContractError
from nornir.core.inventory import Host, Inventory, TransformFunction
from nornir.core.plugins.register import PluginRegister

if TYPE_CHECKING:
    from collections.abc import Callable

INVENTORY_PLUGIN_PATH = "nornir.plugins.inventory"
TRANSFORM_FUNCTION_PLUGIN_PATH = "nornir.plugins.transform_function"
CAPABILITY_INVENTORY_PLUGIN_PATH = "nornir.plugins.capability_inventory"
ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH = "nornir.plugins.async_transform_function"

InventoryCapability = Literal["sync", "asyncio"]


class InventoryPlugin(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the plugin."""
        raise NotImplementedError("needs to be implemented by the plugin")

    def load(self) -> Inventory:
        """Implement the plugin's business logic."""
        raise NotImplementedError("needs to be implemented by the plugin")


class CapabilityInventoryPlugin(Protocol):
    """Common contract for plugins in the capability-aware inventory registry.

    The plugin is constructed with ``inventory.options``. Construction and capability
    reporting perform no I/O. Loading methods are required only for the declared
    capabilities.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the plugin from ``inventory.options``; must not perform I/O."""

    def get_capabilities(self) -> frozenset[InventoryCapability]:
        """Return exactly ``{'sync'}``, ``{'asyncio'}``, or both capabilities."""
        ...


class SyncCapabilityInventoryPlugin(CapabilityInventoryPlugin, Protocol):
    """Capability-aware inventory plugin that loads synchronously."""

    def load(self) -> Inventory:
        """Load the inventory synchronously."""
        ...


class AsyncCapabilityInventoryPlugin(CapabilityInventoryPlugin, Protocol):
    """Capability-aware inventory plugin that loads with a native coroutine."""

    async def aload(self) -> Inventory:
        """Return the same kind of Inventory as ``load``; must not block the event loop."""
        ...


class DualCapabilityInventoryPlugin(
    SyncCapabilityInventoryPlugin, AsyncCapabilityInventoryPlugin, Protocol
):
    """Loaded with ``load`` by InitNornir and with ``aload`` by AInitNornir."""


class AsyncTransformFunction(Protocol):
    """Transform defined with ``async def``; awaited once per host by AInitNornir."""

    async def __call__(self, host: Host, **kwargs: Any) -> None:
        """Enrich one host; receives ``inventory.transform_function_options``."""


InventoryPluginRegister: PluginRegister[type[InventoryPlugin]] = PluginRegister(
    INVENTORY_PLUGIN_PATH
)


TransformFunctionRegister: PluginRegister[TransformFunction] = PluginRegister(
    TRANSFORM_FUNCTION_PLUGIN_PATH
)

# The legacy registers above share PluginRegister's class-level dictionary; the new
# registers get their own so that a name is only found where it was registered.
CapabilityInventoryPluginRegister: PluginRegister[type[CapabilityInventoryPlugin]] = PluginRegister(
    CAPABILITY_INVENTORY_PLUGIN_PATH
)
CapabilityInventoryPluginRegister.available = {}

AsyncTransformFunctionRegister: PluginRegister[AsyncTransformFunction] = PluginRegister(
    ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH
)
AsyncTransformFunctionRegister.available = {}


def _is_sync_capability_inventory_plugin(
    plugin: CapabilityInventoryPlugin,
) -> TypeGuard[SyncCapabilityInventoryPlugin]:
    load = getattr(plugin, "load", None)
    return callable(load) and not inspect.iscoroutinefunction(load)


def _is_async_capability_inventory_plugin(
    plugin: CapabilityInventoryPlugin,
) -> TypeGuard[AsyncCapabilityInventoryPlugin]:
    return inspect.iscoroutinefunction(getattr(plugin, "aload", None))


def _is_dual_capability_inventory_plugin(
    plugin: CapabilityInventoryPlugin,
) -> TypeGuard[DualCapabilityInventoryPlugin]:
    return _is_sync_capability_inventory_plugin(plugin) and _is_async_capability_inventory_plugin(
        plugin
    )


def _validate_capability_inventory_plugin(
    plugin_name: str, plugin: CapabilityInventoryPlugin
) -> frozenset[InventoryCapability]:
    """Check a capability-aware inventory plugin against its contract.

    Arguments:
        plugin_name: Name the plugin was resolved under, used in error messages
        plugin: Constructed plugin instance

    Returns:
        The declared capabilities.

    Raises:
        nornir.core.exceptions.InventoryPluginContractError: the declaration cannot be
            read, is not one of the three valid declarations, or a declared loading
            method is missing or of the wrong kind

    """
    try:
        reporter = getattr(plugin, "get_capabilities", None)
    except Exception as exc:
        raise InventoryPluginContractError(
            plugin_name, "get_capabilities could not be accessed"
        ) from exc
    if not callable(reporter) or inspect.iscoroutinefunction(reporter):
        raise InventoryPluginContractError(
            plugin_name, "get_capabilities must be a synchronous callable"
        )

    try:
        capabilities = reporter()
    except Exception as exc:
        raise InventoryPluginContractError(plugin_name, "get_capabilities failed") from exc

    valid_declarations = (
        frozenset({"sync"}),
        frozenset({"asyncio"}),
        frozenset({"sync", "asyncio"}),
    )
    if not isinstance(capabilities, frozenset) or capabilities not in valid_declarations:
        raise InventoryPluginContractError(
            plugin_name,
            "get_capabilities must return a nonempty frozenset containing only "
            "'sync' and/or 'asyncio'",
        )

    operation_guard: Callable[[CapabilityInventoryPlugin], bool]
    if capabilities == valid_declarations[2]:
        operation_guard = _is_dual_capability_inventory_plugin
        invalid_reason = "dual capability requires a synchronous load and a native async aload"
    elif "sync" in capabilities:
        operation_guard = _is_sync_capability_inventory_plugin
        invalid_reason = "sync capability requires a synchronous load"
    else:
        operation_guard = _is_async_capability_inventory_plugin
        invalid_reason = "asyncio capability requires a native async aload"

    try:
        operations_valid = operation_guard(plugin)
    except Exception as exc:
        raise InventoryPluginContractError(
            plugin_name, "declared loading methods could not be accessed"
        ) from exc

    if not operations_valid:
        raise InventoryPluginContractError(plugin_name, invalid_reason)

    return capabilities
