import os

from nornir.plugins.inventory import SimpleInventory

dir_path = os.path.dirname(os.path.realpath(__file__))


class Test:
    def test(self):
        host_file = f"{dir_path}/data/hosts.yaml"
        group_file = f"{dir_path}/data/groups.yaml"
        defaults_file = f"{dir_path}/data/defaults.yaml"

        inv = SimpleInventory(host_file, group_file, defaults_file).load()
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
                    "data": {"site": "site2"},
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
                    "groups": [],
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
                    "data": {"a_false_var": False, "a_var": "blah"},
                    "groups": [],
                    "hostname": None,
                    "name": "parent_group",
                    "password": "from_parent_group",
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
                    'data': {'smiley': '😜'},
                    "groups": [],
                    "hostname": "localhost",
                    "name": "dev5.no_group",
                    "password": None,
                    "platform": "linux",
                    "port": 65024,
                    "username": None,
                },
            },
        }

    def test_simple_inventory_empty(self):
        """Verify completely empty groups.yaml and defaults.yaml doesn't generate exception."""
        host_file = f"{dir_path}/data/hosts-nogroups.yaml"
        group_file = f"{dir_path}/data/groups-empty.yaml"
        defaults_file = f"{dir_path}/data/defaults-empty.yaml"

        inv = SimpleInventory(host_file, group_file, defaults_file).load()
        assert len(inv.hosts) == 1
        assert inv.groups == {}
        assert inv.defaults.data == {}
