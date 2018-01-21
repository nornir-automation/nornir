Brigade
=======

Now that we know how the inventory works let's create a brigade object we can start working with. There are two ways we can use:

1. Using the :obj:`brigade.core.Brigade` directly, which is quite simple and the most flexible and versatile option.

Using the "raw" API
-------------------

If you want to use the "raw" API you need two things:

1. A :obj:`brigade.core.configuration.Config` object.
2. An :doc:`inventory </ref/inventory/index>` object.

Once you have them, you can create the brigade object yourself. For example::

	>>> from brigade.core import Brigade
	>>> from brigade.core.configuration import Config
	>>> from brigade.plugins.inventory.simple import SimpleInventory
	>>>
	>>> brigade = Brigade(
	...     inventory=SimpleInventory("hosts.yaml", "groups.yaml"),
	...     dry_run=False,
	...     config=Config(raise_on_error=False),
	... )
	>>>

Using ``easy_brigade``
----------------------

	>>> from brigade.easy import easy_brigade
	>>> brigade = easy_brigade(
	...         host_file="hosts.yaml", group_file="groups.yaml",
	...         dry_run=True,
	...         raise_on_error=False,
	... )
	>>>

As you can see is not that different from above but you save a few imports.

Brigade's Inventory
-------------------

Brigade's object will always have a reference to the inventory you can inspect and work with if you have the need. For instance::

    >>> brigade.inventory
    <brigade.plugins.inventory.simple.SimpleInventory object at 0x10606bf28>
    >>> brigade.inventory.hosts
    {'host1.cmh': Host: host1.cmh, 'host2.cmh': Host: host2.cmh, 'spine00.cmh': Host: spine00.cmh, 'spine01.cmh': Host: spine01.cmh, 'leaf00.cmh': Host: leaf00.cmh, 'leaf01.cmh': Host: leaf01.cmh, 'host1.bma': Host: host1.bma, 'host2.bma': Host: host2.bma, 'spine00.bma': Host: spine00.bma, 'spine01.bma': Host: spine01.bma, 'leaf00.bma': Host: leaf00.bma, 'leaf01.bma': Host: leaf01.bma}
    >>> brigade.inventory.groups
    {'all': Group: all, 'bma': Group: bma, 'cmh': Group: cmh}

As you will see further on in the tutorial you will rarely need to work with the inventory yourself as brigade will take care of it for you automatically but it's always good to know you have it there if you need to.

Filtering the hosts
___________________

As we could see in the :doc:`Inventory <inventory>` section we could filter hosts based on data and attributes. The brigade object can leverage on that feature to "replicate" itself with subsets of devices allowing you to group your devices and perform actions on them as you see fit::

    >>> switches = brigade.filter(type="network_device")
    >>> switches.inventory.hosts
    {'spine00.cmh': Host: spine00.cmh, 'spine01.cmh': Host: spine01.cmh, 'leaf00.cmh': Host: leaf00.cmh, 'leaf01.cmh': Host: leaf01.cmh, 'spine00.bma': Host: spine00.bma, 'spine01.bma': Host: spine01.bma, 'leaf00.bma': Host: leaf00.bma, 'leaf01.bma': Host: leaf01.bma}
    >>> switches_in_bma = switches.filter(site="bma")
    >>> switches_in_bma.inventory.hosts
    {'spine00.bma': Host: spine00.bma, 'spine01.bma': Host: spine01.bma, 'leaf00.bma': Host: leaf00.bma, 'leaf01.bma': Host: leaf01.bma}
    >>> hosts = brigade.filter(type="host")
    >>> hosts.inventory.hosts
    {'host1.cmh': Host: host1.cmh, 'host2.cmh': Host: host2.cmh, 'host1.bma': Host: host1.bma, 'host2.bma': Host: host2.bma}

All of the "replicas" of brigade will contain the same data and configuration, only the hosts will differ.
