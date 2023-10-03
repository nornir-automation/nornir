from nornir_utils.plugins.inventory import YAMLInventory

from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.plugins.runners import RunnersPluginRegister
from nornir.plugins.inventory import SimpleInventory
from nornir.plugins.runners import SerialRunner, ThreadedRunner


class Test:
    def test_registered_runners(self):
        RunnersPluginRegister.deregister_all()
        RunnersPluginRegister.auto_register()
        assert RunnersPluginRegister.available == {
            "threaded": ThreadedRunner,
            "serial": SerialRunner,
        }

    def test_registered_inventory(self):
        InventoryPluginRegister.deregister_all()
        InventoryPluginRegister.auto_register()
        assert InventoryPluginRegister.available == {
            "SimpleInventory": SimpleInventory,
            "YAMLInventory": YAMLInventory,
        }
