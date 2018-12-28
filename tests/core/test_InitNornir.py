import os
import pytest


from nornir import InitNornir
from nornir.core.deserializer.inventory import Inventory


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_InitNornir")


def transform_func(host):
    host["processed_by_transform_function"] = True


def transform_func_with_options(host, a):
    host["a"] = a


class StringInventory(Inventory):
    def __init__(self, **kwargs):
        inv_dict = {"hosts": {"host1": {}, "host2": {}}, "groups": {}, "defaults": {}}
        super().__init__(**inv_dict, **kwargs)


class Test(object):
    def test_InitNornir_defaults(self):
        os.chdir("tests/inventory_data/")
        nr = InitNornir()
        os.chdir("../../")
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 20
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_file(self):
        nr = InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 100
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_programmatically(self):
        nr = InitNornir(
            core={"num_workers": 100},
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 100
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_combined(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            core={"num_workers": 200},
        )
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 200
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_different_inventory_by_string(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={"plugin": "tests.core.test_InitNornir.StringInventory"},
        )
        assert "host1" in nr.inventory.hosts

    def test_InitNornir_different_inventory_imported(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={"plugin": StringInventory},
        )
        assert "host1" in nr.inventory.hosts

    def test_InitNornir_different_transform_function_by_string(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "transform_function": "tests.core.test_InitNornir.transform_func",
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        for host in nr.inventory.hosts.values():
            assert host["processed_by_transform_function"]

    def test_InitNornir_different_transform_function_imported(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "transform_function": transform_func,
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        for host in nr.inventory.hosts.values():
            assert host["processed_by_transform_function"]

    def test_InitNornir_different_transform_function_by_string_with_options(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "transform_function": "tests.core.test_InitNornir.transform_func_with_options",
                "transform_function_options": {"a": 1},
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        for host in nr.inventory.hosts.values():
            assert host["a"] == 1

    def test_InitNornir_different_transform_function_by_string_with_bad_options(self):
        with pytest.raises(TypeError):
            nr = InitNornir(
                config_file=os.path.join(dir_path, "a_config.yaml"),
                inventory={
                    "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                    "transform_function": "tests.core.test_InitNornir.transform_func_with_options",
                    "transform_function_options": {"a": 1, "b": 0},
                    "options": {
                        "host_file": "tests/inventory_data/hosts.yaml",
                        "group_file": "tests/inventory_data/groups.yaml",
                    },
                },
            )
            assert nr
