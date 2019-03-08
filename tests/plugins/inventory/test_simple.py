import os

from nornir.plugins.inventory import simple
from nornir.core.deserializer.inventory import Inventory

BASE_PATH = os.path.join(os.path.dirname(__file__), "nsot")


class Test(object):
    def test_inventory(self):
        hosts = {
            "host1": {
                "username": "user",
                "groups": ["group_a"],
                "data": {"a": 1, "b": 2},
            },
            "host2": {"username": "user2", "data": {"a": 1, "b": 2}},
        }
        groups = {"group_a": {"platform": "linux"}}
        defaults = {"data": {"a_default": "asd"}}
        inv = simple.SimpleInventory.deserialize(
            hosts=hosts, groups=groups, defaults=defaults
        )
        assert Inventory.serialize(inv).dict() == {
            "hosts": {
                "host1": {
                    "hostname": None,
                    "port": None,
                    "username": "user",
                    "password": None,
                    "platform": None,
                    "groups": ["group_a"],
                    "data": {"a": 1, "b": 2},
                    "connection_options": {},
                },
                "host2": {
                    "hostname": None,
                    "port": None,
                    "username": "user2",
                    "password": None,
                    "platform": None,
                    "groups": [],
                    "data": {"a": 1, "b": 2},
                    "connection_options": {},
                },
            },
            "groups": {
                "group_a": {
                    "hostname": None,
                    "port": None,
                    "username": None,
                    "password": None,
                    "platform": "linux",
                    "groups": [],
                    "data": {},
                    "connection_options": {},
                }
            },
            "defaults": {
                "hostname": None,
                "port": None,
                "username": None,
                "password": None,
                "platform": None,
                "data": {"a_default": "asd"},
                "connection_options": {},
            },
        }
