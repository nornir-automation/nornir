import os
from builtins import super


from brigade.core import InitBrigade
from brigade.core.inventory import Inventory


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_InitBrigade")


def transform_func(host):
    host.processed_by_transform_function = True


class StringInventory(Inventory):

    def __init__(self, *args, **kwargs):
        hosts = {"host1": {}, "host2": {}}
        super().__init__(hosts, *args, **kwargs)


class Test(object):

    def test_InitBrigade_defaults(self):
        os.chdir("tests/inventory_data/")
        try:
            brg = InitBrigade()
        finally:
            os.chdir("../../")
        assert not brg.dry_run
        assert brg.config.num_workers == 20
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitBrigade_file(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"))
        assert not brg.dry_run
        assert brg.config.num_workers == 100
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitBrigade_programmatically(self):
        brg = InitBrigade(num_workers=100,
                          inventory="brigade.plugins.inventory.simple.SimpleInventory",
                          SimpleInventory={"host_file": "tests/inventory_data/hosts.yaml",
                                           "group_file": "tests/inventory_data/groups.yaml",
                                           },
                          )
        assert not brg.dry_run
        assert brg.config.num_workers == 100
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitBrigade_combined(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          num_workers=200,
                          )
        assert not brg.dry_run
        assert brg.config.num_workers == 200
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_InitBrigade_different_inventory_by_string(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          inventory="tests.core.test_InitBrigade.StringInventory",
                          )
        assert isinstance(brg.inventory, StringInventory)

    def test_InitBrigade_different_inventory_imported(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          inventory=StringInventory,
                          )
        assert isinstance(brg.inventory, StringInventory)

    def test_InitBrigade_different_transform_function_by_string(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          transform_function="tests.core.test_InitBrigade.transform_func",
                          )
        for value in brg.inventory.hosts.values():
            assert value.processed_by_transform_function

    def test_InitBrigade_different_transform_function_imported(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          transform_function=transform_func,
                          )
        for value in brg.inventory.hosts.values():
            assert value.processed_by_transform_function
