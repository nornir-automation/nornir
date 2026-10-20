"""Contract: public API added by 002-async-inventory.

Signatures only. Targets:
  nornir/core/plugins/inventory.py  - capability inventory protocols, async transform, registries
  nornir/core/exceptions.py         - see errors.md
  nornir/init_nornir.py             - AInitNornir, aload_inventory
  nornir/__init__.py                - export AInitNornir
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.inventory import Host, Inventory
from nornir.core.plugins.register import PluginRegister

# --- nornir/core/plugins/inventory.py --------------------------------------------------

CAPABILITY_INVENTORY_PLUGIN_PATH = "nornir.plugins.capability_inventory"
ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH = "nornir.plugins.async_transform_function"

InventoryCapability = Literal["sync", "asyncio"]


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
    def load(self) -> Inventory:
        """Load the inventory synchronously."""
        ...


class AsyncCapabilityInventoryPlugin(CapabilityInventoryPlugin, Protocol):
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


CapabilityInventoryPluginRegister: PluginRegister[type[CapabilityInventoryPlugin]] = PluginRegister(
    CAPABILITY_INVENTORY_PLUGIN_PATH
)
CapabilityInventoryPluginRegister.available = {}  # own dict, see research R6

AsyncTransformFunctionRegister: PluginRegister[AsyncTransformFunction] = PluginRegister(
    ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH
)
AsyncTransformFunctionRegister.available = {}  # own dict, see research R6

# Unchanged: InventoryPlugin, InventoryPluginRegister, TransformFunction,
# TransformFunctionRegister, INVENTORY_PLUGIN_PATH, TRANSFORM_FUNCTION_PLUGIN_PATH.

# --- nornir/init_nornir.py -------------------------------------------------------------


def load_inventory(config: Config) -> Inventory:
    """Load the inventory synchronously; the signature is unchanged.

    Also resolves capability plugins (sync or dual) and raises the errors listed in
    errors.md.
    """


async def aload_inventory(config: Config) -> Inventory:
    """Load the inventory without blocking the loop and without creating one."""


async def AInitNornir(  # noqa: N802 - mirrors InitNornir
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
    """Build a Nornir object; same parameters, defaults and return type as InitNornir."""


# --- nornir/__init__.py ----------------------------------------------------------------
# Export AInitNornir next to InitNornir in __all__.
