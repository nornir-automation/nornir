from typing import Any, Type

from nornir.core.inventory import Inventory, TransformFunction
from nornir.core.plugins.register import PluginRegister

from typing_extensions import Protocol


INVENTORY_PLUGIN_PATH = "nornir.plugins.inventory"
TRANSFORM_FUNCTION_PLUGIN_PATH = "nornir.plugins.transform_function"


class InventoryPlugin(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def load(self) -> Inventory:
        """
        This method implements the plugin's business logic
        """
        raise NotImplementedError("needs to be implemented by the plugin")


InventoryPluginRegister: PluginRegister[Type[InventoryPlugin]] = PluginRegister(
    INVENTORY_PLUGIN_PATH
)


TransformFunctionRegister: PluginRegister[TransformFunction] = PluginRegister(
    TRANSFORM_FUNCTION_PLUGIN_PATH
)
