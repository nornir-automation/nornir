import os

from brigade.core import InitBrigade


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_InitBrigade")


class Test(object):

    def test_InitBrigade_defaults(self):
        os.chdir("tests/core/inventory_data/")
        try:
            brg = InitBrigade()
        finally:
            os.chdir("../../../")
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
                          SimpleInventory={
                              "host_file": "tests/core/inventory_data/hosts.yaml",
                              "group_file": "tests/core/inventory_data/groups.yaml",
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
