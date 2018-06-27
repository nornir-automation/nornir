import os

from nornir.core.filter import F
from nornir.plugins.inventory.simple import SimpleInventory

dir_path = os.path.dirname(os.path.realpath(__file__))
inventory = SimpleInventory(
    "{}/../inventory_data/hosts.yaml".format(dir_path),
    "{}/../inventory_data/groups.yaml".format(dir_path),
)


class Test(object):
    def test_simple(self):
        f = F(site="site1")
        filtered = sorted(list((inventory.filter(filter_func=f).hosts.keys())))
        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_and(self):
        f = F(site="site1") & F(role="www")
        filtered = sorted(list((inventory.filter(filter_func=f).hosts.keys())))
        assert filtered == ["dev1.group_1"]

    def test_or(self):
        f = F(site="site1") | F(role="www")
        filtered = sorted(list((inventory.filter(filter_func=f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1", "dev3.group_2"]

    def test_combined(self):
        f = F(site="site2") | (F(role="www") & F(my_var="comes_from_dev1.group_1"))
        filtered = sorted(list((inventory.filter(filter_func=f).hosts.keys())))
        assert filtered == ["dev1.group_1", "dev3.group_2", "dev4.group_2"]

    def test_contains(self):
        f = F(groups__contains="group_1")
        filtered = sorted(list((inventory.filter(filter_func=f).hosts.keys())))
        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_negate(self):
        f = ~F(groups__contains="group_1")
        filtered = sorted(list((inventory.filter(filter_func=f).hosts.keys())))
        assert filtered == ["dev3.group_2", "dev4.group_2"]
