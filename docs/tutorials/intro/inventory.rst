The Inventory
=============

The inventory is arguably the most important piece of Brigade. The inventory organizes hosts and makes sure tasks have the correct data for each host.


Inventory data
--------------

Before we start let's take a look at the inventory data:

* ``hosts.yaml``

.. literalinclude:: ../../../examples/inventory/hosts.yaml

* ``groups.yaml``

.. literalinclude:: ../../../examples/inventory/groups.yaml

Loading the inventory
---------------------

You can create the inventory in different ways, depending on your data source. To see the available plugins you can use go to the :ref:`ref-inventory` reference guide.

.. note:: For this and the subsequent sections of this tutorial we are going to use the :obj:`SimpleInventory <brigade.plugins.inventory.simple.SimpleInventory>` with the data located in ``/examples/inventory/``. We will also use the ``Vagrantfile`` located there so you should be able to reproduce everything.

First, let's load the inventory::

	>>> from brigade.plugins.inventory.simple import SimpleInventory
	>>> inventory = SimpleInventory(host_file="hosts.yaml", group_file="groups.yaml")

Now let's inspect the hosts and groups we have::

	>>> inventory.hosts
	{'host1.cmh': Host: host1.cmh, 'host2.cmh': Host: host2.cmh, 'spine00.cmh': Host: spine00.cmh, 'spine01.cmh': Host: spine01.cmh, 'leaf00.cmh': Host: leaf00.cmh, 'leaf01.cmh': Host: leaf01.cmh, 'host1.bma': Host: host1.bma, 'host2.bma': Host: host2.bma, 'spine00.bma': Host: spine00.bma, 'spine01.bma': Host: spine01.bma, 'leaf00.bma': Host: leaf00.bma, 'leaf01.bma': Host: leaf01.bma}
	>>> inventory.groups
	{'all': Group: all, 'bma': Group: bma, 'cmh': Group: cmh}

As you probably noticed both ``hosts`` and ``groups`` are dictionaries so you can iterate over them if you want to.

Data
----

Let's start by grabbing a host:

	>>> h = inventory.hosts['host1.cmh']
	>>> print(h)
	host1.cmh

Now, let's check some attributes::

	>>> h["site"]
	'cmh'
	>>> h.data["role"]
	'host'
	>>> h["domain"]
	'acme.com'
	>>> h.data["domain"]
	Traceback (most recent call last):
	  File "<stdin>", line 1, in <module>
	KeyError: 'domain'
	>>> h.group["domain"]
	'acme.com'

What does this mean? You can access host data in two ways:

1. As if the host was a dictionary, i.e., ``h["domain"]`` in which case the inventory will resolve the groups and use data inherited from them (in our example ``domain`` is coming from the parent group).
2. Via the ``data`` attribute in which case there is no group resolution going on so ``h["domain"]`` fails is that piece of data is not directly assigned to the host.

Most of the time you will care about the first option but if you ever need to get data only from the host you can do it without a hassle.

Finally, the host behaves like a python dictionary so you can iterate over the data as such::

	>>> h.keys()
	dict_keys(['name', 'group', 'asn', 'vlans', 'site', 'role', 'brigade_nos', 'type'])
	>>> h.values()
	dict_values(['host1.cmh', 'cmh', 65000, {100: 'frontend', 200: 'backend'}, 'cmh', 'host', 'linux', 'host'])
	>>> h.items()
	dict_items([('name', 'host1.cmh'), ('group', 'cmh'), ('asn', 65000), ('vlans', {100: 'frontend', 200: 'backend'}), ('site', 'cmh'), ('role', 'host'), ('brigade_nos', 'linux'), ('type', 'host')])
	>>> for k, v in h.items():
	...     print(k, v)
	...
	name host1.cmh
	group cmh
	asn 65000
	vlans {100: 'frontend', 200: 'backend'}
	site cmh
	role host
	brigade_nos linux
	type host
	>>>

.. note:: You can head to :obj:`brigade.core.inventory.Host` and :obj:`brigade.core.inventory.Group` for details on all the available attributes and functions for each ``host`` and ``group``.

Filtering the inventory
-----------------------

You won't always want to operate over all hosts, sometimes you will want to operate over some of them based on some attributes. In order to do so the inventory can help you filtering based on it's attributes. For instance::

	>>> inventory.hosts.keys()
	dict_keys(['host1.cmh', 'host2.cmh', 'spine00.cmh', 'spine01.cmh', 'leaf00.cmh', 'leaf01.cmh', 'host1.bma', 'host2.bma', 'spine00.bma', 'spine01.bma', 'leaf00.bma', 'leaf01.bma'])
	>>> inventory.filter(site="bma").hosts.keys()
	dict_keys(['host1.bma', 'host2.bma', 'spine00.bma', 'spine01.bma', 'leaf00.bma', 'leaf01.bma'])
	>>> inventory.filter(site="bma", role="spine").hosts.keys()
	dict_keys(['spine00.bma', 'spine01.bma'])
	>>> inventory.filter(site="bma").filter(role="spine").hosts.keys()
	dict_keys(['spine00.bma', 'spine01.bma'])

Note in the last line that the filter is cumulative so you can do things like this:

	>>> cmh = inventory.filter(site="cmh")
	>>> cmh.hosts.keys()
	dict_keys(['host1.cmh', 'host2.cmh', 'spine00.cmh', 'spine01.cmh', 'leaf00.cmh', 'leaf01.cmh'])
	>>> cmh_eos = cmh.filter(brigade_nos="eos")
	>>> cmh_eos.hosts.keys()
	dict_keys(['spine00.cmh', 'leaf00.cmh'])
	>>> cmh_eos.filter(role="spine").hosts.keys()
	dict_keys(['spine00.cmh'])

This should give you enough room to build groups in any way you want.

Advanced filtering
__________________

You can also do more complex filtering by using functions or lambdas::

	>>> def has_long_name(host):
	...     return len(host.name) == 11
	...
	>>> inventory.filter(filter_func=has_long_name).hosts.keys()
	dict_keys(['spine00.cmh', 'spine01.cmh', 'spine00.bma', 'spine01.bma'])
	>>> inventory.filter(filter_func=lambda h: len(h.name) == 9).hosts.keys()
	dict_keys(['host1.cmh', 'host2.cmh', 'host1.bma', 'host2.bma'])

Not the most useful example but it should be enough to illustrate how it works.
