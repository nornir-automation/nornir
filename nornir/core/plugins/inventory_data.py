from typing import Any, Dict, ItemsView, KeysView, Protocol, Type, ValuesView

from nornir.core.plugins.register import PluginRegister

INVENTORY_DATA_PLUGIN_PATH = "nornir.plugins.inventory_data"


class InventoryData(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def __getitem__(self, key) -> Any:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def get(self, key, default=None) -> Any:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def __setitem__(self, key, value):
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def keys(self) -> KeysView:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def values(self) -> ValuesView:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def items(self) -> ItemsView:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")


class InventoryDataPlugin(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def load(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns the object containing the data
        """
        raise NotImplementedError("needs to be implemented by the plugin")


InventoryDataPluginRegister: PluginRegister[Type[InventoryDataPlugin]] = PluginRegister(
    INVENTORY_DATA_PLUGIN_PATH
)
