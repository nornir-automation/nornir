from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.plugins.runners import RunnersPluginRegister

from nornir.plugins.inventory import SimpleInventory
from nornir.plugins.runners import SerialRunner, ParallelRunner


class Test:
    def test_registered_runners(self):
        RunnersPluginRegister.deregister_all()
        RunnersPluginRegister.auto_register()
        assert RunnersPluginRegister.available == {
            "parallel": ParallelRunner,
            "serial": SerialRunner,
        }

    def test_registered_inventory(self):
        InventoryPluginRegister.deregister_all()
        InventoryPluginRegister.auto_register()
        assert InventoryPluginRegister.available == {
            "SimpleInventory": SimpleInventory,
        }
