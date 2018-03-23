import os

from brigade.core import InitBrigade
from brigade.core.plugins.inventory import NSOTInventory


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_InitBrigade")


def test_transform_function(host):
    host.data["transform_function_test"] = "executed"


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
                          inventory="brigade.plugins.inventory.nsot.NSOTInventory",
                          )
        assert isinstance(brg.inventory, NSOTInventory)

    def test_InitBrigade_different_inventory_imported(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          inventory=NSOTInventory,
                          )
        assert isinstance(brg.inventory, NSOTInventory)

    def test_InitBrigade_different_transform_function_by_string(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          transform_function="brigade.tests.core.test_InitBrigade.test_transform_function",
                          )
        for host in brg.inventory.hosts:
            assert host.data["transform_function_test"] == "executed"

    def test_InitBrigade_different_transform_function_imported(self):
        brg = InitBrigade(config_file=os.path.join(dir_path, "a_config.yaml"),
                          transform_function=test_transform_function,
                          )
        for host in brg.inventory.hosts:
            assert host.data["transform_function_test"] == "executed"
