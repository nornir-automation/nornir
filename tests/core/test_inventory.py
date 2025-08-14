import os

import pytest
import ruamel.yaml

from nornir.core import inventory
from nornir.core.inventory import Host

yaml = ruamel.yaml.YAML(typ="safe")
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(f"{dir_path}/../inventory_data/hosts.yaml") as f:
    hosts = yaml.load(f)
with open(f"{dir_path}/../inventory_data/groups.yaml") as f:
    groups = yaml.load(f)
with open(f"{dir_path}/../inventory_data/defaults.yaml") as f:
    defaults = yaml.load(f)
inv_dict = {"hosts": hosts, "groups": groups, "defaults": defaults}


class Test:
    def test_host(self) -> None:
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

    def test_inventory(self) -> None:
        g1 = inventory.Group(name="g1")
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups([g1]))
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups([g1, g2]))
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

    def test_inventory_data(self, inv: inventory.Inventory) -> None:
        """Test Host values()/keys()/items()"""
        h = inv.hosts["dev1.group_1"]
        assert "comes_from_dev1.group_1" in h.values()
        assert "blah" in h.values()
        assert "my_var" in h.keys()
        assert "only_default" in h.keys()
        assert dict(h.items())["my_var"] == "comes_from_dev1.group_1"

    def test_inventory_dict(self, inv: inventory.Inventory) -> None:
        assert inv.dict() == {
            "defaults": {
                "connection_options": {
                    "dummy": {
                        "extras": {"blah": "from_defaults"},
                        "hostname": "dummy_from_defaults",
                        "password": None,
                        "platform": None,
                        "port": None,
                        "username": None,
                    }
                },
                "data": {
                    "my_var": "comes_from_defaults",
                    "only_default": "only_defined_in_default",
                },
                "hostname": None,
                "password": "docker",
                "platform": "linux",
                "port": None,
                "username": "root",
            },
            "groups": {
                "group_1": {
                    "connection_options": {},
                    "data": {"my_var": "comes_from_group_1", "site": "site1"},
                    "groups": ["parent_group"],
                    "hostname": None,
                    "name": "group_1",
                    "password": "from_group1",
                    "platform": None,
                    "port": None,
                    "username": None,
                },
                "group_2": {
                    "connection_options": {},
                    "data": {
                        "some_string_to_test_any_all": "other_prefix",
                        "site": "site2",
                    },
                    "groups": [],
                    "hostname": None,
                    "name": "group_2",
                    "password": None,
                    "platform": None,
                    "port": None,
                    "username": None,
                },
                "group_3": {
                    "connection_options": {},
                    "data": {"site": "site2"},
                    "groups": ["dummy_group", "parent_group"],
                    "hostname": None,
                    "name": "group_3",
                    "password": None,
                    "platform": None,
                    "port": None,
                    "username": None,
                },
                "parent_group": {
                    "connection_options": {
                        "dummy": {
                            "extras": {"blah": "from_group"},
                            "hostname": "dummy_from_parent_group",
                            "password": None,
                            "platform": None,
                            "port": None,
                            "username": None,
                        },
                        "dummy2": {
                            "extras": {"blah": "from_group"},
                            "hostname": "dummy2_from_parent_group",
                            "password": None,
                            "platform": None,
                            "port": None,
                            "username": None,
                        },
                    },
                    "data": {
                        "a_false_var": False,
                        "a_var": "blah",
                        "my_var": "comes_from_parent_group",
                    },
                    "groups": [],
                    "hostname": None,
                    "name": "parent_group",
                    "password": "from_parent_group",
                    "platform": None,
                    "port": None,
                    "username": None,
                },
                "dummy_group": {
                    "connection_options": {},
                    "data": {},
                    "groups": [],
                    "hostname": None,
                    "name": "dummy_group",
                    "password": None,
                    "platform": None,
                    "port": None,
                    "username": None,
                },
            },
            "hosts": {
                "dev1.group_1": {
                    "connection_options": {
                        "dummy": {
                            "extras": {"blah": "from_host"},
                            "hostname": "dummy_from_host",
                            "password": None,
                            "platform": None,
                            "port": None,
                            "username": None,
                        },
                        "paramiko": {
                            "extras": {},
                            "hostname": None,
                            "password": "docker",
                            "platform": "linux",
                            "port": 65020,
                            "username": "root",
                        },
                    },
                    "data": {
                        "some_string_to_test_any_all": "prefix",
                        "my_var": "comes_from_dev1.group_1",
                        "nested_data": {
                            "a_dict": {"a": 1, "b": 2},
                            "a_list": [1, 2],
                            "a_string": "asdasd",
                        },
                        "role": "www",
                        "www_server": "nginx",
                    },
                    "groups": ["group_1"],
                    "hostname": "localhost",
                    "name": "dev1.group_1",
                    "password": "a_password",
                    "platform": "eos",
                    "port": 65020,
                    "username": None,
                },
                "dev2.group_1": {
                    "connection_options": {
                        "dummy2": {
                            "extras": None,
                            "hostname": None,
                            "password": None,
                            "platform": None,
                            "port": None,
                            "username": "dummy2_from_host",
                        },
                        "paramiko": {
                            "extras": {},
                            "hostname": None,
                            "password": "docker",
                            "platform": "linux",
                            "port": None,
                            "username": "root",
                        },
                    },
                    "data": {
                        "some_string_to_test_any_all": "prefix_longer",
                        "nested_data": {
                            "a_dict": {"b": 2, "c": 3},
                            "a_list": [2, 3],
                            "a_string": "qwe",
                        },
                        "role": "db",
                    },
                    "groups": ["group_1"],
                    "hostname": "localhost",
                    "name": "dev2.group_1",
                    "password": None,
                    "platform": "junos",
                    "port": 65021,
                    "username": None,
                },
                "dev3.group_2": {
                    "connection_options": {
                        "nornir_napalm.napalm": {
                            "extras": {},
                            "hostname": None,
                            "password": None,
                            "platform": "mock",
                            "port": None,
                            "username": None,
                        }
                    },
                    "data": {"role": "www", "www_server": "apache"},
                    "groups": ["group_2"],
                    "hostname": "localhost",
                    "name": "dev3.group_2",
                    "password": None,
                    "platform": "linux",
                    "port": 65022,
                    "username": None,
                },
                "dev4.group_2": {
                    "connection_options": {
                        "netmiko": {
                            "extras": {},
                            "hostname": "localhost",
                            "password": "docker",
                            "platform": "linux",
                            "port": None,
                            "username": "root",
                        },
                        "paramiko": {
                            "extras": {},
                            "hostname": "localhost",
                            "password": "docker",
                            "platform": "linux",
                            "port": None,
                            "username": "root",
                        },
                    },
                    "data": {"my_var": "comes_from_dev4.group_2", "role": "db"},
                    "groups": ["parent_group", "group_2"],
                    "hostname": "localhost",
                    "name": "dev4.group_2",
                    "password": None,
                    "platform": "linux",
                    "port": 65023,
                    "username": None,
                },
                "dev5.no_group": {
                    "connection_options": {},
                    "data": {},
                    "groups": [],
                    "hostname": "localhost",
                    "name": "dev5.no_group",
                    "password": None,
                    "platform": "linux",
                    "port": 65024,
                    "username": None,
                },
                "dev6.group_3": {
                    "connection_options": {},
                    "data": {"asd": 1},
                    "groups": ["group_3"],
                    "hostname": "localhost",
                    "name": "dev6.group_3",
                    "password": None,
                    "platform": "linux",
                    "port": 65025,
                    "username": None,
                },
            },
        }

    def test_extended_data(self, inv: inventory.Inventory) -> None:
        assert inv.hosts["dev1.group_1"].extended_data() == {
            "a_false_var": False,
            "a_var": "blah",
            "my_var": "comes_from_dev1.group_1",
            "nested_data": {
                "a_dict": {"a": 1, "b": 2},
                "a_list": [1, 2],
                "a_string": "asdasd",
            },
            "only_default": "only_defined_in_default",
            "role": "www",
            "site": "site1",
            "some_string_to_test_any_all": "prefix",
            "www_server": "nginx",
        }
        assert inv.hosts["dev3.group_2"].extended_data() == {
            "my_var": "comes_from_defaults",
            "only_default": "only_defined_in_default",
            "role": "www",
            "site": "site2",
            "some_string_to_test_any_all": "other_prefix",
            "www_server": "apache",
        }
        assert inv.hosts["dev5.no_group"].extended_data() == {
            "my_var": "comes_from_defaults",
            "only_default": "only_defined_in_default",
        }
        assert inv.hosts["dev6.group_3"].extended_data() == {
            "a_false_var": False,
            "a_var": "blah",
            "asd": 1,
            "my_var": "comes_from_parent_group",
            "only_default": "only_defined_in_default",
            "site": "site2",
        }

    def test_parent_groups_extended(self, inv: inventory.Inventory) -> None:
        assert inv.hosts["dev1.group_1"].extended_groups() == [
            inv.groups["group_1"],
            inv.groups["parent_group"],
        ]
        assert inv.hosts["dev3.group_2"].extended_groups() == [
            inv.groups["group_2"],
        ]
        assert inv.hosts["dev5.no_group"].extended_groups() == []
        assert inv.hosts["dev6.group_3"].extended_groups() == [
            inv.groups["group_3"],
            inv.groups["dummy_group"],
            inv.groups["parent_group"],
        ]

    def test_filtering(self, inv: inventory.Inventory) -> None:
        unfiltered = sorted(list(inv.hosts.keys()))
        assert unfiltered == [
            "dev1.group_1",
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
            "dev6.group_3",
        ]

        www = sorted(list(inv.filter(role="www").hosts.keys()))
        assert www == ["dev1.group_1", "dev3.group_2"]

        www_site1 = sorted(list(inv.filter(role="www", site="site1").hosts.keys()))
        assert www_site1 == ["dev1.group_1"]

        www_site1 = sorted(list(inv.filter(role="www").filter(site="site1").hosts.keys()))
        assert www_site1 == ["dev1.group_1"]

    def test_filtering_func(self, inv: inventory.Inventory) -> None:
        long_names = sorted(
            list(inv.filter(filter_func=lambda x: len(x["my_var"]) > 20).hosts.keys())
        )
        assert long_names == ["dev1.group_1", "dev4.group_2", "dev6.group_3"]

        def longer_than(dev: Host, length: int) -> bool:
            return len(dev["my_var"]) > length

        long_names = sorted(list(inv.filter(filter_func=longer_than, length=20).hosts.keys()))
        assert long_names == ["dev1.group_1", "dev4.group_2", "dev6.group_3"]

    def test_filter_unique_keys(self, inv: inventory.Inventory) -> None:
        filtered = sorted(list(inv.filter(www_server="nginx").hosts.keys()))
        assert filtered == ["dev1.group_1"]

    def test_var_resolution(self, inv: inventory.Inventory) -> None:
        assert inv.hosts["dev1.group_1"]["my_var"] == "comes_from_dev1.group_1"
        assert inv.hosts["dev2.group_1"]["my_var"] == "comes_from_group_1"
        assert inv.hosts["dev3.group_2"]["my_var"] == "comes_from_defaults"
        assert inv.hosts["dev4.group_2"]["my_var"] == "comes_from_dev4.group_2"
        assert inv.hosts["dev5.no_group"]["my_var"] == "comes_from_defaults"
        assert inv.hosts["dev6.group_3"]["my_var"] == "comes_from_parent_group"
        assert inv.hosts["dev1.group_1"]["a_false_var"] is False

        assert inv.hosts["dev1.group_1"].data["my_var"] == "comes_from_dev1.group_1"
        with pytest.raises(KeyError):
            inv.hosts["dev2.group_1"].data["my_var"]
        with pytest.raises(KeyError):
            inv.hosts["dev3.group_2"].data["my_var"]
        assert inv.hosts["dev4.group_2"].data["my_var"] == "comes_from_dev4.group_2"

    def test_attributes_resolution(self, inv: inventory.Inventory) -> None:
        assert inv.hosts["dev1.group_1"].password == "a_password"
        assert inv.hosts["dev2.group_1"].password == "from_group1"
        assert inv.hosts["dev3.group_2"].password == "docker"
        assert inv.hosts["dev4.group_2"].password == "from_parent_group"
        assert inv.hosts["dev5.no_group"].password == "docker"
        assert inv.hosts["dev6.group_3"].password == "from_parent_group"

    def test_has_parents(self, inv: inventory.Inventory) -> None:
        assert inv.hosts["dev1.group_1"].has_parent_group(inv.groups["group_1"])
        assert not inv.hosts["dev1.group_1"].has_parent_group(inv.groups["group_2"])
        assert inv.hosts["dev1.group_1"].has_parent_group("group_1")
        assert not inv.hosts["dev1.group_1"].has_parent_group("group_2")

    def test_get_connection_parameters(self, inv: inventory.Inventory) -> None:
        p1 = inv.hosts["dev1.group_1"].get_connection_parameters("dummy")
        assert p1.port == 65020
        assert p1.hostname == "dummy_from_host"
        assert p1.username == "root"
        assert p1.password == "a_password"
        assert p1.platform == "eos"
        assert p1.extras == {"blah": "from_host"}
        p2 = inv.hosts["dev1.group_1"].get_connection_parameters("asd")
        assert p2.port == 65020
        assert p2.hostname == "localhost"
        assert p2.username == "root"
        assert p2.password == "a_password"
        assert p2.platform == "eos"
        assert p2.extras == {}
        p3 = inv.hosts["dev2.group_1"].get_connection_parameters("dummy")
        assert p3.port == 65021
        assert p3.hostname == "dummy_from_parent_group"
        assert p3.username == "root"
        assert p3.password == "from_group1"
        assert p3.platform == "junos"
        assert p3.extras == {"blah": "from_group"}
        p4 = inv.hosts["dev3.group_2"].get_connection_parameters("dummy")
        assert p4.port == 65022
        assert p4.hostname == "dummy_from_defaults"
        assert p4.username == "root"
        assert p4.password == "docker"
        assert p4.platform == "linux"
        assert p4.extras == {"blah": "from_defaults"}

    def test_defaults(self, inv: inventory.Inventory) -> None:
        inv.defaults.password = "asd"
        assert inv.defaults.password == "asd"
        assert inv.hosts["dev2.group_1"].password == "from_group1"
        assert inv.hosts["dev3.group_2"].password == "asd"
        assert inv.hosts["dev4.group_2"].password == "from_parent_group"
        assert inv.hosts["dev5.no_group"].password == "asd"

    def test_children_of_str(self, inv: inventory.Inventory) -> None:
        assert inv.children_of_group("parent_group") == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
            inv.hosts["dev4.group_2"],
            inv.hosts["dev6.group_3"],
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

    def test_children_of_obj(self, inv: inventory.Inventory) -> None:
        assert inv.children_of_group(inv.groups["parent_group"]) == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
            inv.hosts["dev4.group_2"],
            inv.hosts["dev6.group_3"],
        }

        assert inv.children_of_group(inv.groups["group_1"]) == {
            inv.hosts["dev1.group_1"],
            inv.hosts["dev2.group_1"],
        }

        assert inv.children_of_group(inv.groups["group_2"]) == {
            inv.hosts["dev4.group_2"],
            inv.hosts["dev3.group_2"],
        }

    def test_add_host(self) -> None:
        data = {"test_var": "test_value"}
        defaults = inventory.Defaults(data=data)
        g1 = inventory.Group(name="g1")
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups([g1]))
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups([g1, g2]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups, defaults=defaults)
        h3_connection_options = inventory.ConnectionOptions(extras={"device_type": "cisco_ios"})
        inv.hosts["h3"] = inventory.Host(
            name="h3",
            groups=[g1],
            platform="TestPlatform",
            connection_options={"netmiko": h3_connection_options},
            defaults=defaults,
        )
        assert "h3" in inv.hosts
        assert "g1" in [i.name for i in inv.hosts["h3"].groups]
        assert "test_var" in inv.hosts["h3"].defaults.data.keys()
        assert inv.hosts["h3"].defaults.data.get("test_var") == "test_value"
        assert inv.hosts["h3"].platform == "TestPlatform"
        assert inv.hosts["h3"].connection_options["netmiko"].extras["device_type"] == "cisco_ios"

    def test_add_group(self) -> None:
        connection_options = {"username": "test_user", "password": "test_pass"}
        data = {"test_var": "test_value"}
        defaults = inventory.Defaults(data=data, connection_options=connection_options)
        g1 = inventory.Group(name="g1")
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups([g1]))
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups([g1, g2]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups, defaults=defaults)
        g3_connection_options = inventory.ConnectionOptions(extras={"device_type": "cisco_ios"})
        inv.groups["g3"] = inventory.Group(
            name="g3",
            username="test_user",
            connection_options={"netmiko": g3_connection_options},
            defaults=defaults,
        )
        assert "g1" in [i.name for i in inv.groups["g2"].groups]
        assert "g3" in inv.groups
        assert inv.groups["g3"].defaults.connection_options.get("username") == "test_user"
        assert inv.groups["g3"].defaults.connection_options.get("password") == "test_pass"
        assert "test_var" in inv.groups["g3"].defaults.data.keys()
        assert inv.groups["g3"].defaults.data.get("test_var") == "test_value"
        assert inv.groups["g3"].connection_options["netmiko"].extras["device_type"] == "cisco_ios"

    def test_dict(self, inv: inventory.Inventory) -> None:
        inventory_dict = inv.dict()
        def_extras = inventory_dict["defaults"]["connection_options"]["dummy"]["extras"]
        grp_data = inventory_dict["groups"]["group_1"]["data"]
        host_data = inventory_dict["hosts"]["dev1.group_1"]["data"]
        assert isinstance(inventory_dict, dict)
        assert inventory_dict["defaults"]["username"] == "root"
        assert def_extras["blah"] == "from_defaults"
        assert "my_var" and "site" in grp_data
        assert "www_server" and "role" in host_data

    def test_get_defaults_dict(self, inv: inventory.Inventory) -> None:
        defaults_dict = inv.defaults.dict()
        con_options = defaults_dict["connection_options"]["dummy"]
        assert isinstance(defaults_dict, dict)
        assert defaults_dict["username"] == "root"
        assert con_options["hostname"] == "dummy_from_defaults"
        assert "blah" in con_options["extras"]

    def test_get_groups_dict(self, inv: inventory.Inventory) -> None:
        groups_dict = {n: g.dict() for n, g in inv.groups.items()}
        assert isinstance(groups_dict, dict)
        assert groups_dict["group_1"]["password"] == "from_group1"
        assert groups_dict["group_2"]["data"]["site"] == "site2"

    def test_get_hosts_dict(self, inv: inventory.Inventory) -> None:
        hosts_dict = {n: h.dict() for n, h in inv.hosts.items()}
        dev1_groups = hosts_dict["dev1.group_1"]["groups"]
        dev2_paramiko_opts = hosts_dict["dev2.group_1"]["connection_options"]["paramiko"]
        assert isinstance(hosts_dict, dict)
        assert "group_1" in dev1_groups
        assert dev2_paramiko_opts["username"] == "root"
        assert "dev3.group_2" in hosts_dict

    def test_add_group_to_host_runtime(self) -> None:
        orig_data = {"var1": "val1"}
        data = {"var3": "val3"}
        g1 = inventory.Group(name="g1", data=orig_data)
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups([g1]))
        g3 = inventory.Group(name="g3", groups=inventory.ParentGroups([g2]), data=data)
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups([g1, g2]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups)

        assert "h1" in inv.hosts
        assert g3 not in inv.hosts["h1"].groups
        assert h1.get("var3", None) is None

        h1.groups.add(g3)
        assert g3 in h1.groups
        assert h1.get("var3", None) == "val3"

    def test_remove_group_from_host(self) -> None:
        data = {"var3": "val3"}
        orig_data = {"var1": "val1"}
        g1 = inventory.Group(name="g1", data=orig_data)
        g2 = inventory.Group(name="g2", groups=inventory.ParentGroups([g1]))
        g3 = inventory.Group(name="g3", groups=inventory.ParentGroups([g2]), data=data)
        h1 = inventory.Host(name="h1", groups=inventory.ParentGroups([g1, g2, g3]))
        h2 = inventory.Host(name="h2")
        hosts = {"h1": h1, "h2": h2}
        groups = {"g1": g1, "g2": g2}
        inv = inventory.Inventory(hosts=hosts, groups=groups)

        assert "h1" in inv.hosts
        assert g3 in inv.hosts["h1"].groups
        assert h1.get("var3") == "val3"

        g3.data["var3"] = "newval3"
        assert h1.get("var3", None) == "newval3"

        h1.groups.remove(g3)
        assert g3 not in h1.groups
        assert h1.get("var3", None) is None
        assert h1.get("var1", None) == "val1"

        with pytest.raises(ValueError):
            h1.groups.remove(g3)
