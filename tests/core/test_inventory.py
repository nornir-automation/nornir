import os

from nornir.core.inventory import Group, Host
from nornir.plugins.inventory.simple import SimpleInventory

import pytest


dir_path = os.path.dirname(os.path.realpath(__file__))
inventory = SimpleInventory(
    "{}/../inventory_data/hosts.yaml".format(dir_path),
    "{}/../inventory_data/groups.yaml".format(dir_path),
)


def compare_lists(left, right):
    result = len(left) == len(right)
    if not result:
        return result

    def to_sets(l):
        if isinstance(l, str):
            return l

        r = set()
        for x in l:
            if isinstance(x, list) or isinstance(x, tuple):
                x = frozenset(to_sets(x))
            r.add(x)
        return r

    left = to_sets(left)
    right = to_sets(right)
    return left == right


class Test(object):

    def test_hosts(self):
        defaults = {"var4": "ALL"}
        g1 = Group(name="g1", var1="1", var2="2", var3="3")
        g2 = Group(name="g2", var1="a", var2="b")
        g3 = Group(name="g3", var1="A", var4="Z")
        g4 = Group(name="g4", groups=[g2, g1], var3="q")

        h1 = Host(name="host1", groups=[g1, g2], defaults=defaults)
        assert h1["var1"] == "1"
        assert h1["var2"] == "2"
        assert h1["var3"] == "3"
        assert h1["var4"] == "ALL"
        assert compare_lists(
            list(h1.keys()), ["name", "groups", "var1", "var2", "var3", "var4"]
        )
        assert compare_lists(
            list(h1.values()), ["host1", ["g1", "g2"], "1", "2", "3", "ALL"]
        )
        assert compare_lists(
            list(h1.items()),
            [
                ("name", "host1"),
                ("groups", ["g1", "g2"]),
                ("var1", "1"),
                ("var2", "2"),
                ("var3", "3"),
                ("var4", "ALL"),
            ],
        )

        h2 = Host(name="host2", groups=[g2, g1], defaults=defaults)
        assert h2["var1"] == "a"
        assert h2["var2"] == "b"
        assert h2["var3"] == "3"
        assert h2["var4"] == "ALL"
        assert compare_lists(
            list(h2.keys()), ["name", "groups", "var1", "var2", "var3", "var4"]
        )
        assert compare_lists(
            list(h2.values()), ["host2", ["g2", "g1"], "a", "b", "3", "ALL"]
        )
        assert compare_lists(
            list(h2.items()),
            [
                ("name", "host2"),
                ("groups", ["g2", "g1"]),
                ("var1", "a"),
                ("var2", "b"),
                ("var3", "3"),
                ("var4", "ALL"),
            ],
        )

        h3 = Host(name="host3", groups=[g4, g3], defaults=defaults)
        assert h3["var1"] == "a"
        assert h3["var2"] == "b"
        assert h3["var3"] == "q"
        assert h3["var4"] == "Z"
        assert compare_lists(
            list(h3.keys()), ["name", "groups", "var3", "var1", "var2", "var4"]
        )
        assert compare_lists(
            list(h3.values()), ["host3", ["g4", "g3"], "q", "a", "b", "Z"]
        )
        assert compare_lists(
            list(h3.items()),
            [
                ("name", "host3"),
                ("groups", ["g4", "g3"]),
                ("var3", "q"),
                ("var1", "a"),
                ("var2", "b"),
                ("var4", "Z"),
            ],
        )

        h4 = Host(name="host4", groups=[g3, g4], defaults=defaults)
        assert h4["var1"] == "A"
        assert h4["var2"] == "b"
        assert h4["var3"] == "q"
        assert h4["var4"] == "Z"
        assert compare_lists(
            list(h4.keys()), ["name", "groups", "var1", "var4", "var3", "var2"]
        )
        assert compare_lists(
            list(h4.values()), ["host4", ["g3", "g4"], "A", "Z", "q", "b"]
        )
        assert compare_lists(
            list(h4.items()),
            [
                ("name", "host4"),
                ("groups", ["g3", "g4"]),
                ("var1", "A"),
                ("var4", "Z"),
                ("var3", "q"),
                ("var2", "b"),
            ],
        )

        with pytest.raises(KeyError):
            assert h2["asdasd"]

    def test_filtering(self):
        unfiltered = sorted(list(inventory.hosts.keys()))
        assert (
            unfiltered
            == ["dev1.group_1", "dev2.group_1", "dev3.group_2", "dev4.group_2"]
        )

        www = sorted(list(inventory.filter(role="www").hosts.keys()))
        assert www == ["dev1.group_1", "dev3.group_2"]

        www_site1 = sorted(
            list(inventory.filter(role="www", site="site1").hosts.keys())
        )
        assert www_site1 == ["dev1.group_1"]

        www_site1 = sorted(
            list(inventory.filter(role="www").filter(site="site1").hosts.keys())
        )
        assert www_site1 == ["dev1.group_1"]

    def test_filtering_func(self):
        long_names = sorted(
            list(
                inventory.filter(
                    filter_func=lambda x: len(x["my_var"]) > 20
                ).hosts.keys()
            )
        )
        assert long_names == ["dev1.group_1", "dev4.group_2"]

        def longer_than(dev, length):
            return len(dev["my_var"]) > length

        long_names = sorted(
            list(inventory.filter(filter_func=longer_than, length=20).hosts.keys())
        )
        assert long_names == ["dev1.group_1", "dev4.group_2"]

    def test_filter_unique_keys(self):
        filtered = sorted(list(inventory.filter(www_server="nginx").hosts.keys()))
        assert filtered == ["dev1.group_1"]

    def test_var_resolution(self):
        assert inventory.hosts["dev1.group_1"]["my_var"] == "comes_from_dev1.group_1"
        assert inventory.hosts["dev2.group_1"]["my_var"] == "comes_from_group_1"
        assert inventory.hosts["dev3.group_2"]["my_var"] == "comes_from_defaults"
        assert inventory.hosts["dev4.group_2"]["my_var"] == "comes_from_dev4.group_2"

        assert (
            inventory.hosts["dev1.group_1"].data["my_var"] == "comes_from_dev1.group_1"
        )
        with pytest.raises(KeyError):
            inventory.hosts["dev2.group_1"].data["my_var"]
        with pytest.raises(KeyError):
            inventory.hosts["dev3.group_2"].data["my_var"]
        assert (
            inventory.hosts["dev4.group_2"].data["my_var"] == "comes_from_dev4.group_2"
        )

    def test_has_parents(self):
        assert inventory.hosts["dev1.group_1"].has_parent_group(
            inventory.groups["group_1"]
        )
        assert not inventory.hosts["dev1.group_1"].has_parent_group(
            inventory.groups["group_2"]
        )
