import os

from nornir.core import inventory
from nornir.core.deserializer import inventory as deserializer

from pydantic import ValidationError

import pytest

import ruamel.yaml


yaml = ruamel.yaml.YAML(typ="safe")
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
        h = inventory.Host(name="host1", hostname="host1")
        assert h.hostname == "host1"
        assert h.port is None
        assert h.username is None
        assert h.password is None
        assert h.platform is None
        assert h.data == {}

        data = {"asn": 65100, "router_id": "1.1.1.1"}
        h = inventory.Host(
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
        g1 = inventory.Group(name="g1")
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups(["g1"]))
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups(["g1", "g2"]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups)
        assert "h1" in inv.hosts
        assert "h2" in inv.hosts
        assert "g1" in inv.groups
        assert "g2" in inv.groups
        assert inv.groups["g1"] in inv.hosts["h1"].groups
        assert inv.groups["g1"] in inv.groups["g2"].groups

    def test_inventory_deserializer_wrong(self):
        with pytest.raises(ValidationError):
            deserializer.Inventory.deserialize(
                **{"hosts": {"wrong": {"host": "should_be_hostname"}}}
            )

    def test_inventory_deserializer(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        assert inv.groups["group_1"] in inv.hosts["dev1.group_1"].groups

    def test_inventory_data(self):
        """Test Host values()/keys()/items()"""
        inv = deserializer.Inventory.deserialize(**inv_dict)
        h = inv.hosts["dev1.group_1"]
        assert "comes_from_dev1.group_1" in h.values()
        assert "blah" in h.values()
        assert "my_var" in h.keys()
        assert "only_default" in h.keys()
        assert "comes_from_dev1.group_1" == dict(h.items())["my_var"]

    def test_filtering(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        unfiltered = sorted(list(inv.hosts.keys()))
        assert unfiltered == [
            "dev1.group_1",
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
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
        inv = deserializer.Inventory.deserialize(**inv_dict)
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
        inv = deserializer.Inventory.deserialize(**inv_dict)
        filtered = sorted(list(inv.filter(www_server="nginx").hosts.keys()))
        assert filtered == ["dev1.group_1"]

    def test_var_resolution(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        assert inv.hosts["dev1.group_1"]["my_var"] == "comes_from_dev1.group_1"
        assert inv.hosts["dev2.group_1"]["my_var"] == "comes_from_group_1"
        assert inv.hosts["dev3.group_2"]["my_var"] == "comes_from_defaults"
        assert inv.hosts["dev4.group_2"]["my_var"] == "comes_from_dev4.group_2"
        assert inv.hosts["dev1.group_1"]["a_false_var"] is False

        assert inv.hosts["dev1.group_1"].data["my_var"] == "comes_from_dev1.group_1"
        with pytest.raises(KeyError):
            inv.hosts["dev2.group_1"].data["my_var"]
        with pytest.raises(KeyError):
            inv.hosts["dev3.group_2"].data["my_var"]
        assert inv.hosts["dev4.group_2"].data["my_var"] == "comes_from_dev4.group_2"

    def test_attributes_resolution(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        assert inv.hosts["dev1.group_1"].password == "a_password"
        assert inv.hosts["dev2.group_1"].password == "from_group1"
        assert inv.hosts["dev3.group_2"].password == "docker"
        assert inv.hosts["dev4.group_2"].password == "from_parent_group"
        assert inv.hosts["dev5.no_group"].password == "docker"

    def test_has_parents(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        assert inv.hosts["dev1.group_1"].has_parent_group(inv.groups["group_1"])
        assert not inv.hosts["dev1.group_1"].has_parent_group(inv.groups["group_2"])
        assert inv.hosts["dev1.group_1"].has_parent_group("group_1")
        assert not inv.hosts["dev1.group_1"].has_parent_group("group_2")

    def test_to_dict(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        inv_serialized = deserializer.Inventory.serialize(inv).dict()
        for k, v in inv_dict.items():
            assert v == inv_serialized[k]

    def test_get_connection_parameters(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        p1 = inv.hosts["dev1.group_1"].get_connection_parameters("dummy")
        assert deserializer.ConnectionOptions.serialize(p1).dict() == {
            "port": 22,
            "hostname": "dummy_from_host",
            "username": "root",
            "password": "a_password",
            "platform": "eos",
            "extras": {"blah": "from_host"},
        }
        p2 = inv.hosts["dev1.group_1"].get_connection_parameters("asd")
        assert deserializer.ConnectionOptions.serialize(p2).dict() == {
            "port": 22,
            "hostname": "dev1.group_1",
            "username": "root",
            "password": "a_password",
            "platform": "eos",
            "extras": {},
        }
        p3 = inv.hosts["dev2.group_1"].get_connection_parameters("dummy")
        assert deserializer.ConnectionOptions.serialize(p3).dict() == {
            "port": 22,
            "hostname": "dummy_from_parent_group",
            "username": "root",
            "password": "from_group1",
            "platform": "junos",
            "extras": {"blah": "from_group"},
        }
        p4 = inv.hosts["dev3.group_2"].get_connection_parameters("dummy")
        assert deserializer.ConnectionOptions.serialize(p4).dict() == {
            "port": 22,
            "hostname": "dummy_from_defaults",
            "username": "root",
            "password": "docker",
            "platform": "linux",
            "extras": {"blah": "from_defaults"},
        }

    def test_defaults(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        inv.defaults.password = "asd"
        assert inv.defaults.password == "asd"
        assert inv.hosts["dev2.group_1"].password == "from_group1"
        assert inv.hosts["dev3.group_2"].password == "asd"
        assert inv.hosts["dev4.group_2"].password == "from_parent_group"
        assert inv.hosts["dev5.no_group"].password == "asd"

    def test_children_of_str(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        assert inv.children_of_group("parent_group") == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
            inv.hosts["dev4.group_2"],
        }

        assert inv.children_of_group("group_1") == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
        }

        assert inv.children_of_group("group_2") == {
            inv.hosts["dev4.group_2"],
            inv.hosts["dev3.group_2"],
        }

        assert inv.children_of_group("blah") == set()

    def test_children_of_obj(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        assert inv.children_of_group(inv.groups["parent_group"]) == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
            inv.hosts["dev4.group_2"],
        }

        assert inv.children_of_group(inv.groups["group_1"]) == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
        }

        assert inv.children_of_group(inv.groups["group_2"]) == {
            inv.hosts["dev4.group_2"],
            inv.hosts["dev3.group_2"],
        }

    def test_add_host(self):
        data = {"test_var": "test_value"}
        defaults = inventory.Defaults(data=data)
        g1 = inventory.Group(name="g1")
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups(["g1"]))
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups(["g1", "g2"]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups, defaults=defaults)
        h3_connection_options = {"netmiko": {"extras": {"device_type": "cisco_ios"}}}
        inv.add_host(
            name="h3",
            groups=["g1"],
            platform="TestPlatform",
            connection_options=h3_connection_options,
        )
        assert "h3" in inv.hosts
        assert "g1" in [i.name for i in inv.hosts["h3"].groups.refs]
        assert "test_var" in inv.hosts["h3"].defaults.data.keys()
        assert inv.hosts["h3"].defaults.data.get("test_var") == "test_value"
        assert inv.hosts["h3"].platform == "TestPlatform"
        assert (
            inv.hosts["h3"].connection_options["netmiko"].extras["device_type"]
            == "cisco_ios"
        )
        with pytest.raises(KeyError):
            inv.add_host(name="h4", groups=["not_defined"])
        # Test with one good and one undefined group
        with pytest.raises(KeyError):
            inv.add_host(name="h5", groups=["g1", "not_defined"])

    def test_add_group(self):
        connection_options = {"username": "test_user", "password": "test_pass"}
        data = {"test_var": "test_value"}
        defaults = inventory.Defaults(data=data, connection_options=connection_options)
        g1 = inventory.Group(name="g1")
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups(["g1"]))
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups(["g1", "g2"]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups, defaults=defaults)
        g3_connection_options = {"netmiko": {"extras": {"device_type": "cisco_ios"}}}
        inv.add_group(
            name="g3", username="test_user", connection_options=g3_connection_options
        )
        assert "g1" in [i.name for i in inv.groups["g2"].groups.refs]
        assert "g3" in inv.groups
        assert (
            inv.groups["g3"].defaults.connection_options.get("username") == "test_user"
        )
        assert (
            inv.groups["g3"].defaults.connection_options.get("password") == "test_pass"
        )
        assert "test_var" in inv.groups["g3"].defaults.data.keys()
        assert "test_value" == inv.groups["g3"].defaults.data.get("test_var")
        assert (
            inv.groups["g3"].connection_options["netmiko"].extras["device_type"]
            == "cisco_ios"
        )
        # Test with one undefined parent group
        with pytest.raises(KeyError):
            inv.add_group(name="g4", groups=["undefined"])
        # Test with one defined and one undefined parent group
        with pytest.raises(KeyError):
            inv.add_group(name="g4", groups=["g1", "undefined"])

    def test_dict(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        inventory_dict = inv.dict()
        def_extras = inventory_dict["defaults"]["connection_options"]["dummy"]["extras"]
        grp_data = inventory_dict["groups"]["group_1"]["data"]
        host_data = inventory_dict["hosts"]["dev1.group_1"]["data"]
        assert type(inventory_dict) == dict
        assert inventory_dict["defaults"]["username"] == "root"
        assert def_extras["blah"] == "from_defaults"
        assert "my_var" and "site" in grp_data
        assert "www_server" and "role" in host_data

    def test_get_inventory_dict(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        inventory_dict = inv.get_inventory_dict()
        def_extras = inventory_dict["defaults"]["connection_options"]["dummy"]["extras"]
        grp_data = inventory_dict["groups"]["group_1"]["data"]
        host_data = inventory_dict["hosts"]["dev1.group_1"]["data"]
        assert type(inventory_dict) == dict
        assert inventory_dict["defaults"]["username"] == "root"
        assert def_extras["blah"] == "from_defaults"
        assert "my_var" and "site" in grp_data
        assert "www_server" and "role" in host_data

    def test_get_defaults_dict(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        defaults_dict = inv.get_defaults_dict()
        con_options = defaults_dict["connection_options"]["dummy"]
        assert type(defaults_dict) == dict
        assert defaults_dict["username"] == "root"
        assert con_options["hostname"] == "dummy_from_defaults"
        assert "blah" in con_options["extras"]

    def test_get_groups_dict(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        groups_dict = inv.get_groups_dict()
        assert type(groups_dict) == dict
        assert groups_dict["group_1"]["password"] == "from_group1"
        assert groups_dict["group_2"]["data"]["site"] == "site2"

    def test_get_hosts_dict(self):
        inv = deserializer.Inventory.deserialize(**inv_dict)
        hosts_dict = inv.get_hosts_dict()
        dev1_groups = hosts_dict["dev1.group_1"]["groups"]
        dev2_paramiko_opts = hosts_dict["dev2.group_1"]["connection_options"][
            "paramiko"
        ]
        assert type(hosts_dict) == dict
        assert "group_1" in dev1_groups
        assert dev2_paramiko_opts["username"] == "root"
        assert "dev3.group_2" in hosts_dict
