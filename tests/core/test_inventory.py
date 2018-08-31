import os

from nornir.core.inventory import Group, Host, Inventory
from nornir.core.serializer import InventorySerializer

from pydantic import ValidationError

import pytest

import ruamel.yaml


yaml = ruamel.yaml.YAML()
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(f"{dir_path}/../inventory_data/hosts.yaml") as f:
    hosts = yaml.load(f)
with open(f"{dir_path}/../inventory_data/groups.yaml") as f:
    groups = yaml.load(f)
with open(f"{dir_path}/../inventory_data/defaults.yaml") as f:
    defaults = yaml.load(f)
inv_dict = {"hosts": hosts, "groups": groups, "defaults": defaults}


class Test(object):
    def test_host(self):
        h = Host(name="host1", hostname="host1")
        assert h.hostname == "host1"
        assert h.port is None
        assert h.username is None
        assert h.password is None
        assert h.platform is None
        assert h.data == {}

        data = {"asn": 65100, "router_id": "1.1.1.1"}
        h = Host(
            name="host2",
            hostname="host2",
            username="user",
            port=123,
            password="",
            platform="fake",
            data=data,
        )
        assert h.hostname == "host2"
        assert h.port == 123
        assert h.username == "user"
        assert h.password == ""
        assert h.platform == "fake"
        assert h.data == data

    def test_inventory(self):
        g1 = Group(name="g1")
        g2 = Group(name="g2", groups=[g1])
        h1 = Host(name="h1", groups=[g1, g2])
        h2 = Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inventory = Inventory(hosts=hosts, groups=groups)
        assert "h1" in inventory.hosts
        assert "h2" in inventory.hosts
        assert "g1" in inventory.groups
        assert "g2" in inventory.groups
        assert inventory.groups["g1"] in inventory.hosts["h1"].groups
        assert inventory.groups["g1"] in inventory.groups["g2"].groups

    def test_inventory_deserializer_wrong(self):
        with pytest.raises(ValidationError):
            InventorySerializer.deserialize(
                {"hosts": {"wrong": {"host": "should_be_hostname"}}}
            )

    def test_inventory_deserializer(self):
        inv = InventorySerializer.deserialize(inv_dict)
        assert inv.groups["group_1"] in inv.hosts["dev1.group_1"].groups

    def test_filtering(self):
        inv = InventorySerializer.deserialize(inv_dict)
        unfiltered = sorted(list(inv.hosts.keys()))
        assert unfiltered == [
            "dev1.group_1",
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
        ]

        www = sorted(list(inv.filter(role="www").hosts.keys()))
        assert www == ["dev1.group_1", "dev3.group_2"]

        www_site1 = sorted(list(inv.filter(role="www", site="site1").hosts.keys()))
        assert www_site1 == ["dev1.group_1"]

        www_site1 = sorted(
            list(inv.filter(role="www").filter(site="site1").hosts.keys())
        )
        assert www_site1 == ["dev1.group_1"]

    def test_filtering_func(self):
        inv = InventorySerializer.deserialize(inv_dict)
        long_names = sorted(
            list(inv.filter(filter_func=lambda x: len(x["my_var"]) > 20).hosts.keys())
        )
        assert long_names == ["dev1.group_1", "dev4.group_2"]

        def longer_than(dev, length):
            return len(dev["my_var"]) > length

        long_names = sorted(
            list(inv.filter(filter_func=longer_than, length=20).hosts.keys())
        )
        assert long_names == ["dev1.group_1", "dev4.group_2"]

    def test_filter_unique_keys(self):
        inv = InventorySerializer.deserialize(inv_dict)
        filtered = sorted(list(inv.filter(www_server="nginx").hosts.keys()))
        assert filtered == ["dev1.group_1"]

    def test_var_resolution(self):
        inv = InventorySerializer.deserialize(inv_dict)
        assert inv.hosts["dev1.group_1"]["my_var"] == "comes_from_dev1.group_1"
        assert inv.hosts["dev2.group_1"]["my_var"] == "comes_from_group_1"
        assert inv.hosts["dev3.group_2"]["my_var"] == "comes_from_defaults"
        assert inv.hosts["dev4.group_2"]["my_var"] == "comes_from_dev4.group_2"

        assert inv.hosts["dev1.group_1"].data["my_var"] == "comes_from_dev1.group_1"
        with pytest.raises(KeyError):
            inv.hosts["dev2.group_1"].data["my_var"]
        with pytest.raises(KeyError):
            inv.hosts["dev3.group_2"].data["my_var"]
        assert inv.hosts["dev4.group_2"].data["my_var"] == "comes_from_dev4.group_2"

        assert inv.hosts["dev1.group_1"].password == "a_password"
        assert inv.hosts["dev2.group_1"].password == "docker"

    def test_has_parents(self):
        inv = InventorySerializer.deserialize(inv_dict)
        assert inv.hosts["dev1.group_1"].has_parent_group(inv.groups["group_1"])
        assert not inv.hosts["dev1.group_1"].has_parent_group(inv.groups["group_2"])
        assert inv.hosts["dev1.group_1"].has_parent_group("group_1")
        assert not inv.hosts["dev1.group_1"].has_parent_group("group_2")

    def test_to_dict(self):
        inv = InventorySerializer.deserialize(inv_dict)
        assert InventorySerializer.serialize(inv).dict() == inv_dict
