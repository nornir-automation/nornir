from typing import (
    Any,
    Dict,
    ItemsView,
    KeysView,
    Optional,
    Protocol,
    Type,
    Union,
    ValuesView,
)

from nornir.core.plugins.register import PluginRegister

INVENTORY_DATA_PLUGIN_PATH = "nornir.plugins.inventory_data"


class InventoryData(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def __getitem__(self, key: str) -> Any:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def get(self, key: str, default: Any = None) -> Any:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def __setitem__(self, key: str, value: Any) -> None:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def keys(self) -> KeysView[str]:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def values(self) -> ValuesView[Any]:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def items(self) -> ItemsView[str, Any]:
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

    def load(
        self, data: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], InventoryData]:
        """
        Returns the object containing the data
        """
        raise NotImplementedError("needs to be implemented by the plugin")


InventoryDataPluginRegister: PluginRegister[Type[InventoryDataPlugin]] = PluginRegister(
    INVENTORY_DATA_PLUGIN_PATH
)
