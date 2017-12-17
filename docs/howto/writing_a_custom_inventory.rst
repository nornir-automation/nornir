Writing a custom inventory
==========================

If you have your own backend with host information or you don't like the provided ones you can write your own custom inventory. Doing so is quite easy. A continuation you can find a very simple one with static data::

    from builtins import super

    from brigade.core.inventory import Inventory


    class MyInventory(Inventory):

        def __init__(self, **kwargs):
            # code to get the data
            hosts = {
                "host1": {
                    "data1": "value1",
                    "data2": "value2".
                    "group": "my_group1",
                },
                "host2": {
                    "data1": "value1",
                    "data2": "value2".
                    "group": "my_group1",
                }
            }
            groups = {
                "my_group1": {
                    "more_data1": "more_value1",
                    "more_data2": "more_value2",
                }
            }

            # passing the data to the parent class so the data is
            # transformed into actual Host/Group objects
            super().__init__(hosts, groups, **kwargs)


So if you want to make it dynamic everything you have to do is get the data yourself and organize it in a similar format to the one described in the example above.

.. note:: it is not mandatory to use groups. Feel free to skip the attribute ``group`` and just pass and empty dict or ``None`` to ``super()``.

Finally, to have brigade use it, you can do::

    inv = MyInventory()
    brigade = Brigade(inventory=inv)

And that's it, you now have your own inventory plugin :)
