import logging
from typing import Any, Dict, Optional, Union

from nornir.core.plugins.inventory_data import InventoryData

logger = logging.getLogger(__name__)


class InventoryDataDict:
    def __init__(self) -> None:
        """
        This method configures the plugin
        """
        ...

    def load(
        self, data: Optional[Dict[str, Any]]
    ) -> Union[Dict[str, Any], InventoryData]:
        """
        Returns the object containing the data
        """
        if data is None:
            return dict()
        return data
