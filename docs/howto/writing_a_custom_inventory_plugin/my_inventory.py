from nornir.core.deserializer.inventory import Inventory


class MyInventory(Inventory):
    def __init__(self, **kwargs):
        # code to get the data
        hosts = {
            "host1": {
                "data": {"data1": "value1", "data2": "value2", "data3": "value3"},
                "groups": ["my_group1"],
            },
            "host2": {
                "data": {"data1": "value1", "data2": "value2", "data3": "value3"},
                "groups": ["my_group1"],
            },
        }
        groups = {
            "my_group1": {
                "data": {
                    "more_data1": "more_value1",
                    "more_data2": "more_value2",
                    "more_data3": "more_value3",
                }
            }
        }
        defaults = {"data": {"location": "internet", "language": "Python"}}

        # passing the data to the parent class so the data is
        # transformed into actual Host/Group objects
        # and set default data for all hosts
        super().__init__(hosts=hosts, groups=groups, defaults=defaults, **kwargs)
