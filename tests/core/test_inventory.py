import os

from brigade.plugins.inventory.simple import SimpleInventory

import pytest


dir_path = os.path.dirname(os.path.realpath(__file__))
inventory = SimpleInventory("{}/inventory_data/hosts.yaml".format(dir_path),
                            "{}/inventory_data/groups.yaml".format(dir_path))


class Test(object):

    def test_filtering(self):
        unfiltered = sorted(list(inventory.hosts.keys()))
        assert unfiltered == ['host1.group_1', 'host2.group_1', 'host3.group_2', 'host4.group_2']

        www = sorted(list(inventory.filter(role="www").hosts.keys()))
        assert www == ['host1.group_1', 'host3.group_2']

        www_site1 = sorted(list(inventory.filter(role="www", site="site1").hosts.keys()))
        assert www_site1 == ['host1.group_1']

        www_site1 = sorted(list(inventory.filter(role="www").filter(site="site1").hosts.keys()))
        assert www_site1 == ['host1.group_1']

    def test_filtering_func(self):
        long_names = sorted(list(inventory.filter(
            filter_func=lambda x: len(x["my_var"]) > 20).hosts.keys()))
        assert long_names == ['host1.group_1', 'host4.group_2']

        def longer_than(host, length):
            return len(host["my_var"]) > length

        long_names = sorted(list(inventory.filter(
            filter_func=longer_than, length=20).hosts.keys()))
        assert long_names == ['host1.group_1', 'host4.group_2']

    def test_filter_unique_keys(self):
        filtered = sorted(list(inventory.filter(www_server='nginx').hosts.keys()))
        assert filtered == ['host1.group_1']

    def test_var_resolution(self):
        assert inventory.hosts["host1.group_1"]["my_var"] == "comes_from_host1.group_1"
        assert inventory.hosts["host2.group_1"]["my_var"] == "comes_from_group_1"
        assert inventory.hosts["host3.group_2"]["my_var"] == "comes_from_all"
        assert inventory.hosts["host4.group_2"]["my_var"] == "comes_from_host4.group_2"

        assert inventory.hosts["host1.group_1"].data["my_var"] == "comes_from_host1.group_1"
        with pytest.raises(KeyError):
            inventory.hosts["host2.group_1"].data["my_var"]
        with pytest.raises(KeyError):
            inventory.hosts["host3.group_2"].data["my_var"]
        assert inventory.hosts["host4.group_2"].data["my_var"] == "comes_from_host4.group_2"
