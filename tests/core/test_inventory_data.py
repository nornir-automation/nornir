# import os

# import pytest
# import ruamel.yaml

from typing import Any, Dict, ItemsView, KeysView, ValuesView

from nornir.core import inventory
from nornir.core.configuration import Config, InventoryDataConfig
from nornir.core.plugins.inventory_data import InventoryDataPluginRegister

# yaml = ruamel.yaml.YAML(typ="safe")
# dir_path = os.path.dirname(os.path.realpath(__file__))
# with open(f"{dir_path}/../inventory_data/hosts.yaml") as f:
#     hosts = yaml.load(f)
# with open(f"{dir_path}/../inventory_data/groups.yaml") as f:
#     groups = yaml.load(f)
# with open(f"{dir_path}/../inventory_data/defaults.yaml") as f:
#     defaults = yaml.load(f)
# inv_dict = {"hosts": hosts, "groups": groups, "defaults": defaults}


class MockInventoryData:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    def __getitem__(self, key) -> Any:
        """
        This method configures the plugin
        """
        return self.data[key]

    def get(self, key, default=None) -> Any:
        """
        This method configures the plugin
        """
        return self.data.get(key, default)

    def __setitem__(self, key, value):
        """
        This method configures the plugin
        """
        self.data[key] = value

    def keys(self) -> KeysView:
        """
        This method configures the plugin
        """
        return self.data.keys()

    def values(self) -> ValuesView:
        """
        This method configures the plugin
        """
        return self.data.values()

    def items(self) -> ItemsView:
        """
        This method configures the plugin
        """
        return self.data.items()


class MockInventoryDataPlugin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        This method configures the plugin
        """
        ...

    def load(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns the object containing the data
        """
        return MockInventoryData(data=data)


class Test(object):
    @classmethod
    def setup_class(cls):
        InventoryDataPluginRegister.deregister_all()
        InventoryDataPluginRegister.register(
            "MockInventoryDataPlugin", MockInventoryDataPlugin
        )

    def test_host(self):
        config = Config(
            inventory_data=InventoryDataConfig(plugin="MockInventoryDataPlugin")
        )
        h = inventory.Host(
            name="host1",
            hostname="host1",
            data={"test": "test123"},
            configuration=config,
        )
        assert h.hostname == "host1"
        assert isinstance(h.data, MockInventoryData)
        assert h.data["test"] == "test123"
        assert h.get("test") == "test123"

    def test_group(self):
        config = Config(
            inventory_data=InventoryDataConfig(plugin="MockInventoryDataPlugin")
        )
        g = inventory.Group(
            name="group1", data={"test": "test123"}, configuration=config
        )
        assert g.name == "group1"
        assert isinstance(g.data, MockInventoryData)
        assert g.data["test"] == "test123"
        assert g.data.get("test") == "test123"

    def test_default(self):
        config = Config(
            inventory_data=InventoryDataConfig(plugin="MockInventoryDataPlugin")
        )
        d = inventory.Defaults(data={"test": "test123"}, configuration=config)
        assert isinstance(d.data, MockInventoryData)
        assert d.data["test"] == "test123"
        assert d.data.get("test") == "test123"

    def test_inventory_data(self):
        config = Config(
            inventory_data=InventoryDataConfig(plugin="MockInventoryDataPlugin")
        )
        g1 = inventory.Group(
            name="g1", data={"g1": "group1 data"}, configuration=config
        )
        g2 = inventory.Group(
            name="g2",
            groups=inventory.ParentGroups([g1]),
            data={"g2": "group2 data"},
            configuration=config,
        )
        h1 = inventory.Host(
            name="h1",
            groups=inventory.ParentGroups([g1, g2]),
            data={"host_data": "host 1"},
            configuration=config,
        )
        h2 = inventory.Host(
            name="h2", data={"host_data": "host 2"}, configuration=config
        )
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups)

        assert list(inv.hosts["h2"].keys()) == ["host_data"]
        assert "host_data" in inv.hosts["h1"].keys()
        assert "g1" in inv.hosts["h1"].keys()
        assert "g2" in inv.hosts["h1"].keys()
        assert len(inv.hosts["h1"].items()) == 3
        assert len(inv.hosts["h1"].values()) == 3

        assert inv.hosts["h1"].get("host_data") == "host 1"
        assert inv.hosts["h1"].get("g1") == "group1 data"
        assert inv.hosts["h1"].get("g2") == "group2 data"

        assert inv.hosts["h1"].extended_data() == {
            "host_data": "host 1",
            "g1": "group1 data",
            "g2": "group2 data",
        }
        assert inv.hosts["h2"].extended_data() == {
            "host_data": "host 2",
        }

    def test_inventory_data_default(self):
        config = Config(
            inventory_data=InventoryDataConfig(plugin="MockInventoryDataPlugin")
        )
        d = inventory.Defaults(data={"default": "default data"}, configuration=config)
        h1 = inventory.Host(
            name="h1", data={"host_data": "host 1"}, defaults=d, configuration=config
        )
        hosts = {"h1": h1}
        inv = inventory.Inventory(hosts=hosts, defaults=d)

        assert inv.hosts["h1"].get("host_data") == "host 1"
        assert inv.hosts["h1"].get("default") == "default data"
        assert len(inv.hosts["h1"].keys()) == 2
        assert len(inv.hosts["h1"].items()) == 2
        assert len(inv.hosts["h1"].values()) == 2

        assert inv.hosts["h1"].extended_data() == {
            "host_data": "host 1",
            "default": "default data",
        }
