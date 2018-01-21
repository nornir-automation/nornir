import os

from brigade.core import from_conf


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_from_conf")


class Test(object):

    def test_from_conf_file(self):
        brg = from_conf(config_file=os.path.join(dir_path, "a_config.yaml"))
        assert not brg.dry_run
        assert brg.config.num_workers == 100
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)

    def test_from_conf_programmatically(self):
        brg = from_conf(num_workers=100,
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

    def test_from_conf_combined(self):
        brg = from_conf(config_file=os.path.join(dir_path, "a_config.yaml"),
                        num_workers=200,
                        )
        assert not brg.dry_run
        assert brg.config.num_workers == 200
        assert len(brg.inventory.hosts)
        assert len(brg.inventory.groups)
