Transforming Inventory Data
===========================

Imagine your data looks like::

    host1:
        username: my_user
        password: my_password
    host2:
        username: my_user
        password: my_password

It turns out nornir is going to look for ``nornir_username`` and ``nornir_password`` to use as credentials. You may not want to change the data in your backend and you may not want to write a custom inventory plugin just to accommodate this difference. Fortunately, ``nornir`` has you covered. You can write a function to do all the data manipulations you want and pass it to any inventory plugin. For instance::

    def adapt_host_data(host):
        host.data["nornir_username"] = host.data["username"]
        host.data["nornir_password"] = host.data["password"]


    inv = NSOTInventory(transform_function=adapt_host_data)
    nornir = Nornir(inventory=inv)

What's going to happen is that the inventory is going to create the :obj:`nornir.core.inventory.Host` and :obj:`nornir.core.inventory.Group` objects as usual and then finally the ``transform_function`` is going to be called for each individual host one by one.

.. note:: This was a very simple example but the ``transform_function`` can basically do anything you want/need.
