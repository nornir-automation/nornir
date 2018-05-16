import os
from builtins import super


from nornir.core import InitNornir
from nornir.core.inventory import Inventory


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_InitNornir")


def transform_func(host):
    host.processed_by_transform_function = True


class StringInventory(Inventory):

    def __init__(self, *args, **kwargs):
        hosts = {"host1": {}, "host2": {}}
        super().__init__(hosts, *args, **kwargs)


class Test(object):

    def test_InitNornir_defaults(self):
        os.chdir("tests/inventory_data/")
        try:
            brg = InitNornir()
        finally:
            os.chdir("../../")
        assert not brg.dry_run
        assert brg.config.num_workers == 20
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitNornir_file(self):
        brg = InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        assert not brg.dry_run
        assert brg.config.num_workers == 100
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitNornir_programmatically(self):
        brg = InitNornir(
            num_workers=100,
            inventory="nornir.plugins.inventory.simple.SimpleInventory",
            SimpleInventory={
                "host_file": "tests/inventory_data/hosts.yaml",
                "group_file": "tests/inventory_data/groups.yaml",
            },
        )
        assert not brg.dry_run
        assert brg.config.num_workers == 100
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitNornir_combined(self):
        brg = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"), num_workers=200
        )
        assert not brg.dry_run
        assert brg.config.num_workers == 200
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitNornir_different_inventory_by_string(self):
        brg = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory="tests.core.test_InitNornir.StringInventory",
        )
        assert isinstance(brg.inventory, StringInventory)

    def test_InitNornir_different_inventory_imported(self):
        brg = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory=StringInventory,
        )
        assert isinstance(brg.inventory, StringInventory)

    def test_InitNornir_different_transform_function_by_string(self):
        brg = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            transform_function="tests.core.test_InitNornir.transform_func",
        )
        for value in brg.inventory.hosts.values():
            assert value.processed_by_transform_function

    def test_InitNornir_different_transform_function_imported(self):
        brg = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            transform_function=transform_func,
        )
        for value in brg.inventory.hosts.values():
            assert value.processed_by_transform_function
