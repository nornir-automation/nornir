#  from nornir.core.filter import F
from nornir.core.filter_parser import parse


class Test(object):
    def test_simple(self, nornir):
        # f = F(site="site1")
        f = parse("site == 'site1'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_and(self, nornir):
        #  f = F(site="site1") & F(role="www")
        f = parse("site == 'site1' AND role == 'www'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_or(self, nornir):
        #  f = F(site="site1") | F(role="www")
        f = parse("site == 'site1' OR role == 'www'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1", "dev3.group_2"]

    def test_combined(self, nornir):
        #  f = F(site="site2") | (F(role="www") & F(my_var="comes_from_dev1.group_1"))
        f = parse(
            "site == 'site2' OR (role == 'www' AND my_var == 'comes_from_dev1.group_1')"
        )
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev3.group_2", "dev4.group_2"]

        #  f = (F(site="site2") | F(role="www")) & F(my_var="comes_from_dev1.group_1")
        f = parse(
            "(site == 'site2' OR role == 'www') AND my_var == 'comes_from_dev1.group_1'"
        )
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

        #  f = F(site="site2") | F(role="www") & F(my_var="comes_from_dev1.group_1")
        f = parse(
            "site == 'site2' OR role == 'www' AND my_var == 'comes_from_dev1.group_1'"
        )
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev3.group_2", "dev4.group_2"]

    def test_contains(self, nornir):
        #  f = F(groups__contains="group_1")
        f = parse("groups contains 'group_1'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_negate(self, nornir):
        #  f = ~F(groups__contains="group_1")
        f = parse("NOT (groups contains 'group_1')")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev3.group_2", "dev4.group_2", "dev5.no_group"]

    def test_negate_and_second_negate(self, nornir):
        #  f = F(site="site1") & ~F(role="www")
        f = parse("site == 'site1' AND NOT(role == 'www')")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev2.group_1"]

        f = parse("site == 'site1' AND role != 'www'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev2.group_1"]

    def test_negate_or_both_negate(self, nornir):
        #  f = ~F(site="site1") | ~F(role="www")
        f = parse('site != "site1" OR role != "www"')
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
        ]

        f = parse('NOT site == "site1" OR NOT role == "www"')
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
        ]

    def test_nested_data_a_string(self, nornir):
        #  f = F(nested_data__a_string="asdasd")
        f = parse("nested_data__a_string == 'asdasd'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_string_contains(self, nornir):
        #  f = F(nested_data__a_string__contains="asd")
        f = parse("nested_data__a_string__contains == 'asd'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_contains(self, nornir):
        #  f = F(nested_data__a_dict__contains="a")
        f = parse("nested_data__a_dict__contains=='a'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_element(self, nornir):
        #  f = F(nested_data__a_dict__a=1)
        f = parse("nested_data__a_dict__a == 1")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_doesnt_contain(self, nornir):
        #  f = ~F(nested_data__a_dict__contains="a")
        f = parse("NOT nested_data__a_dict__contains=='a'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
        ]

    def test_nested_data_a_list_contains(self, nornir):
        #  f = F(nested_data__a_list__contains=2)
        f = parse("nested_data__a_list__contains == 2")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_by_callable_has_parent_group(self, nornir):
        #  f = F(has_parent_group="parent_group")
        f = parse("has_parent_group == 'parent_group'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1", "dev4.group_2"]

    def test_filtering_by_attribute_name(self, nornir):
        #  f = F(name="dev1.group_1")
        f = parse("name=='dev1.group_1'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_filtering_string_in_list(self, nornir):
        #  f = F(platform__in=["linux", "mock"])
        f = parse("platform__in==['linux', 'mock']")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev3.group_2", "dev4.group_2", "dev5.no_group"]

    def test_filtering_list_any(self, nornir):
        #  f = F(nested_data__a_list__any=[1, 3])
        f = parse("nested_data__a_list__any==[1, 3]")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_list_all(self, nornir):
        #  f = F(nested_data__a_list__all=[1, 2])
        f = parse("nested_data__a_list__all==[1, 2]")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_filter_wrong_attribute_for_type(self, nornir):
        #  f = F(port__startswith="a")
        f = parse("port__startswith=='a'")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == []
