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
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_and(self):
        f = F(site="site1") & F(role="www")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_or(self):
        f = F(site="site1") | F(role="www")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1", "dev3.group_2"]

    def test_combined(self):
        f = F(site="site2") | (F(role="www") & F(my_var="comes_from_dev1.group_1"))
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev3.group_2", "dev4.group_2"]

        f = (F(site="site2") | F(role="www")) & F(my_var="comes_from_dev1.group_1")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_contains(self):
        f = F(groups__contains="group_1")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_negate(self):
        f = ~F(groups__contains="group_1")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev3.group_2", "dev4.group_2"]

    def test_negate_and_second_negate(self):
        f = F(site="site1") & ~F(role="www")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev2.group_1"]

    def test_negate_or_both_negate(self):
        f = ~F(site="site1") | ~F(role="www")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev2.group_1", "dev3.group_2", "dev4.group_2"]

    def test_nested_data_a_string(self):
        f = F(nested_data__a_string="asdasd")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_string_contains(self):
        f = F(nested_data__a_string__contains="asd")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_contains(self):
        f = F(nested_data__a_dict__contains="a")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_element(self):
        f = F(nested_data__a_dict__a=1)
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_doesnt_contain(self):
        f = ~F(nested_data__a_dict__contains="a")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev2.group_1", "dev3.group_2", "dev4.group_2"]

    def test_nested_data_a_list_contains(self):
        f = F(nested_data__a_list__contains=2)
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_by_callable_has_parent_group(self):
        f = F(has_parent_group="parent_group")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_by_attribute_name(self):
        f = F(name="dev1.group_1")
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_filtering_string_in_list(self):
        f = F(device_type__in=["linux", "mock"])
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev3.group_2", "dev4.group_2"]

    def test_filtering_list_any(self):
        f = F(nested_data__a_list__any=[1, 3])
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_list_all(self):
        f = F(nested_data__a_list__all=[1, 2])
        filtered = sorted(list((inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]
