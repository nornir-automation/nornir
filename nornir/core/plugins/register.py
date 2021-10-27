import sys
from typing import Dict, TypeVar, Generic

from nornir.core.exceptions import (
    PluginAlreadyRegistered,
    PluginNotRegistered,
)

if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata


T = TypeVar("T")


class PluginRegister(Generic[T]):
    available: Dict[str, T] = {}

    def __init__(self, entry_point: str) -> None:
        self._entry_point = entry_point

    def auto_register(self) -> None:
        for entry_point in metadata.entry_points(group=self._entry_point):
            self.register(entry_point.name, entry_point.load())

    def register(self, name: str, plugin: T) -> None:
        """Registers a plugin with a specified name

        Args:
            name: name of the connection plugin to register
            plugin: plugin class

        Raises:
            :obj:`nornir.core.exceptions.PluginAlreadyRegistered` if
                another plugin with the specified name was already registered
        """
        existing_plugin = self.available.get(name)
        if existing_plugin is None:
            self.available[name] = plugin
        elif existing_plugin != plugin:
            raise PluginAlreadyRegistered(
                f"plugin {plugin} can't be registered as "
                f"{name!r} because plugin {existing_plugin} "
                f"was already registered under this name"
            )

    def deregister(self, name: str) -> None:
        """Deregisters a registered plugin by its name

        Args:
            name: name of the plugin to deregister

        Raises:
            :obj:`nornir.core.exceptions.PluginNotRegistered`
        """
        if name not in self.available:
            raise PluginNotRegistered(f"plugin {name!r} is not registered")
        self.available.pop(name)

    def deregister_all(self) -> None:
        """Deregisters all registered plugins"""
        self.available = {}

    def get_plugin(self, name: str) -> T:
        """Fetches the plugin by name if already registered

        Args:
            name: name of the plugin

        Raises:
            :obj:`nornir.core.exceptions.PluginNotRegistered`
        """
        if name not in self.available:
            raise PluginNotRegistered(f"plugin {name!r} is not registered")
        return self.available[name]
