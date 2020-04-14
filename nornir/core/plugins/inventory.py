from typing import Tuple

from nornir.core.inventory import Groups, Hosts, Defaults
from nornir.core.plugins.register import PluginRegister

from typing_extensions import Protocol


class InventoryPlugin(Protocol):
    def load(self) -> Tuple[Hosts, Groups, Defaults]:
        """
        This method implements the plugin's business logic
        """
        raise NotImplementedError("needs to be implemented by the plugin")


InventoryPluginRegister: PluginRegister[InventoryPlugin] = PluginRegister(
    "nornir.plugins.inventory"
)
