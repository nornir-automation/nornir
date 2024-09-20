import pytest

from nornir.core import Nornir
from nornir.core.filter import AND, OR, F


class Test:
    def test_simple(self, nornir: Nornir) -> None:
        f = F(site="site1")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_and(self, nornir: Nornir) -> None:
        f = F(site="site1") & F(role="www")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_or(self, nornir: Nornir) -> None:
        f = F(site="site1") | F(role="www")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1", "dev3.group_2"]

    def test_combined(self, nornir: Nornir) -> None:
        f = F(site="site2") | (F(role="www") & F(my_var="comes_from_dev1.group_1"))
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev1.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev6.group_3",
        ]

        f = (F(site="site2") | F(role="www")) & F(my_var="comes_from_dev1.group_1")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_contains(self, nornir: Nornir) -> None:
        f = F(groups__contains="group_1")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_negate(self, nornir: Nornir) -> None:
        f = ~F(groups__contains="group_1")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
            "dev6.group_3",
        ]

    def test_negate_and_second_negate(self, nornir: Nornir) -> None:
        f = F(site="site1") & ~F(role="www")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev2.group_1"]

    def test_negate_or_both_negate(self, nornir: Nornir) -> None:
        f = ~F(site="site1") | ~F(role="www")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
            "dev6.group_3",
        ]

    def test_nested_data_a_string(self, nornir: Nornir) -> None:
        f = F(nested_data__a_string="asdasd")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_string_contains(self, nornir: Nornir) -> None:
        f = F(nested_data__a_string__contains="asd")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_contains(self, nornir: Nornir) -> None:
        f = F(nested_data__a_dict__contains="a")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_element(self, nornir: Nornir) -> None:
        f = F(nested_data__a_dict__a=1)
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_nested_data_a_dict_doesnt_contain(self, nornir: Nornir) -> None:
        f = ~F(nested_data__a_dict__contains="a")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev2.group_1",
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
            "dev6.group_3",
        ]

    def test_nested_data_a_list_contains(self, nornir: Nornir) -> None:
        f = F(nested_data__a_list__contains=2)
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_by_callable_has_parent_group(self, nornir: Nornir) -> None:
        f = F(has_parent_group="parent_group")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev1.group_1",
            "dev2.group_1",
            "dev4.group_2",
            "dev6.group_3",
        ]

    def test_filtering_by_attribute_name(self, nornir: Nornir) -> None:
        f = F(name="dev1.group_1")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_filtering_string_in_list(self, nornir: Nornir) -> None:
        f = F(platform__in=["linux", "mock"])
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == [
            "dev3.group_2",
            "dev4.group_2",
            "dev5.no_group",
            "dev6.group_3",
        ]

    def test_filtering_string_any(self, nornir: Nornir) -> None:
        f = F(some_string_to_test_any_all__any=["prefix", "other_prefix"])
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev3.group_2", "dev4.group_2"]

    def test_filtering_list_any(self, nornir: Nornir) -> None:
        f = F(nested_data__a_list__any=[1, 3])
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1", "dev2.group_1"]

    def test_filtering_list_all(self, nornir: Nornir) -> None:
        f = F(nested_data__a_list__all=[1, 2])
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == ["dev1.group_1"]

    def test_filter_wrong_attribute_for_type(self, nornir: Nornir) -> None:
        f = F(port__startswith="a")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == []

    def test_eq__on_not_existing_key(self, nornir: Nornir) -> None:
        f = F(not_existing__eq="test")
        filtered = sorted(list((nornir.inventory.filter(f).hosts.keys())))

        assert filtered == []

    @pytest.mark.parametrize(
        "filter_a,filter_b",
        [
            (F(), F()),
            (F(site="site1") & F(role="www"), AND(F(site="site1"), F(role="www"))),
            (F(site="site1") & F(role="www"), AND(F(role="www"), F(site="site1"))),
            (F(site="site1") | F(role="www"), OR(F(site="site1"), F(role="www"))),
            (F(site="site1") | F(role="www"), OR(F(role="www"), F(site="site1"))),
        ],
    )
    def test_compare_filter_equal(self, filter_a: F, filter_b: F) -> None:
        assert filter_a == filter_b

    @pytest.mark.parametrize(
        "filter_a,filter_b",
        [
            (OR(F(site="site1"), F(role="www")), AND(F(site="site1"), F(role="www"))),
            (F(site="site1"), F(role="www")),
            (F(site="site1"), ~F(site="site1")),
        ],
    )
    def test_compare_filter_not_equal(self, filter_a: F, filter_b: F) -> None:
        assert filter_a != filter_b
