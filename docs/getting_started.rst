Getting Started
###############

Inventory
=========

Let's start by seeing how to work with the inventory. Let's assume the following files:

* Hosts file:

.. literalinclude:: ../demo/hosts.yaml
   :name: hosts.yaml
   :language: yaml
   :linenos:

* Groups file:

.. literalinclude:: ../demo/groups.yaml
   :name: groups.yaml
   :language: yaml
   :linenos:

We can instantiate Brigade as follows::

    >>> from brigade.core import Brigade
    >>> from brigade.plugins.inventory.simple import SimpleInventory
    >>> brigade = Brigade(
    ...         inventory=SimpleInventory("hosts.yaml", "groups.yaml"),
    ...         dry_run=True)
    >>> brigade.inventory.hosts.keys()
    dict_keys(['host1.cmh', 'host2.cmh', 'switch00.cmh', 'switch01.cmh', 'host1.bma', 'host2.bma', 'switch00.bma', 'switch01.bma'])
    >>> brigade.inventory.groups.keys()
    dict_keys(['all', 'bma-leaf', 'bma-host', 'bma', 'cmh-leaf', 'cmh-host', 'cmh'])

As you can see instantiating brigade and providing inventory information is very easy. Now let's see how we can filter hosts. This will be useful when we want to apply certain tasks to only certain devices::

    >>> brigade.filter(site="cmh").inventory.hosts.keys()
    dict_keys(['host1.cmh', 'host2.cmh', 'switch00.cmh', 'switch01.cmh'])
    >>> brigade.filter(site="cmh", role="leaf").inventory.hosts.keys()
    dict_keys(['switch00.cmh', 'switch01.cmh'])

You can basically filter by any attribute the device has. The filter is also cumulative::

    >>> cmh = brigade.filter(site="cmh")
    >>> cmh.inventory.hosts.keys()
    dict_keys(['host1.cmh', 'host2.cmh', 'switch00.cmh', 'switch01.cmh'])
    >>> cmh.filter(role="leaf").inventory.hosts.keys()
    dict_keys(['switch00.cmh', 'switch01.cmh'])

Data
====

Now let's see how to access data. Let's start by grabbing a host::

    >>> host = brigade.inventory.hosts["switch00.cmh"]

Now, you can access host data either via the host itself, as it behaves like a dict, or via it's ``data`` attribute. The difference is that if access data via the host itself the information will be resolved and data inherited by parent groups will be accessible while if you access the data via the ``data`` attribute only data belonging to the host will be accessible. Let's see a few examples, refer to the files on top of this document for reference::

    >>> host["nos"]
    'eos'
    >>> host.data["nos"]
    'eos'
    >>> host["domain"]
    'acme.com'
    >>> host.domain["domain"]
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    AttributeError: 'Host' object has no attribute 'domain'

You can access the parent group via the ``group`` attribute and :obj:`brigade.core.inventory.Group` behave in the same exact way as :obj:`brigade.core.inventory.Host`::

    >>> host.group
    Group: cmh-leaf
    >>> host.group["domain"]
    'acme.com'
    >>> host.group.data["domain"]
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    KeyError: 'domain'

Tasks
=====

Now we know how to deal with the inventory let's try to use plugin to gather device information::

    >>> from brigade.plugins import tasks
    >>> cmh_leaf = brigade.filter(site="cmh", role="leaf")
    >>> result = cmh_leaf.run(task=tasks.napalm_get_facts,
    ...                       facts="facts")
    >>> print(result)
    {'switch00.cmh': {'result': {'hostname': 'switch00.cmh', 'fqdn': 'switch00.cmh.cmh.acme.com', 'vendor': 'Arista', 'model': 'vEOS', 'serial_number': '', 'os_version': '4.17.5M-4414219.4175M', 'uptime': 83187, 'interface_list': ['Ethernet1', 'Ethernet2', 'Management1']}}, 'switch01.cmh': {'result': {'vendor': 'Juniper', 'model': 'FIREFLY-PERIMETER', 'serial_number': 'a7defdc362ff', 'os_version': '12.1X47-D20.7', 'hostname': 'switch01.cmh', 'fqdn': 'switch01.cmh.cmh.acme.com', 'uptime': 83084, 'interface_list': ['ge-0/0/0', 'gr-0/0/0', 'ip-0/0/0', 'lsq-0/0/0', 'lt-0/0/0', 'mt-0/0/0', 'sp-0/0/0', 'ge-0/0/1', 'ge-0/0/2', '.local.', 'dsc', 'gre', 'ipip', 'irb', 'lo0', 'lsi', 'mtun', 'pimd', 'pime', 'pp0', 'ppd0', 'ppe0', 'st0', 'tap', 'vlan']}}}

You can also group multiple tasks into a single block::

    >>> def get_info(task):
    ...     # Grouping multiple tasks that go together
    ...     r = tasks.napalm_get_facts(task, "facts")
    ...     print(task.host.name)
    ...     print("============")
    ...     print(r["result"])
    ...     r = tasks.napalm_get_facts(task, "interfaces")
    ...     print(task.host.name)
    ...     print("============")
    ...     print(r["result"])
    ...     print()
    ...
    >>> cmh_leaf.run(task=get_info)
    switch00.cmh
    ============
    {'hostname': 'switch00.bma', 'fqdn': 'switch00.bma.bma.acme.com', 'vendor': 'Arista', 'model': 'vEOS', 'serial_number': '', 'os_version': '4.17.5M-4414219.4175M', 'uptime': 83424, 'interface_list': ['Ethernet1', 'Ethernet2', 'Management1']}
    switch00.cmh
    ============
    {'Ethernet2': {'is_up': False, 'is_enabled': False, 'description': 'Another interface in bma', 'last_flapped': 1511034159.0399787, 'speed': 0, 'mac_address': '08:00:27:AB:42:B6'}, 'Management1': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 1511033376.7964435, 'speed': 1000, 'mac_address': '08:00:27:47:87:83'}, 'Ethernet1': {'is_up': True, 'is_enabled': True, 'description': 'An Interface in bma', 'last_flapped': 1511033362.0302556, 'speed': 0, 'mac_address': '08:00:27:2D:F4:5A'}}

    switch01.cmh
    ============
    {'vendor': 'Juniper', 'model': 'FIREFLY-PERIMETER', 'serial_number': 'a7defdc362ff', 'os_version': '12.1X47-D20.7', 'hostname': 'switch01.bma', 'fqdn': 'switch01.bma.bma.acme.com', 'uptime': 83320, 'interface_list': ['ge-0/0/0', 'gr-0/0/0', 'ip-0/0/0', 'lsq-0/0/0', 'lt-0/0/0', 'mt-0/0/0', 'sp-0/0/0', 'ge-0/0/1', 'ge-0/0/2', '.local.', 'dsc', 'gre', 'ipip', 'irb', 'lo0', 'lsi', 'mtun', 'pimd', 'pime', 'pp0', 'ppd0', 'ppe0', 'st0', 'tap', 'vlan']}
    switch01.cmh
    ============
    {'ge-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 83272.0, 'mac_address': '08:00:27:AA:8C:76', 'speed': 1000}, 'gr-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'ip-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'lsq-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 83273.0, 'mac_address': 'None', 'speed': -1}, 'lt-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': '02:96:14:8C:76:B3', 'speed': 800}, 'mt-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'sp-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 83273.0, 'mac_address': 'Unspecified', 'speed': 800}, 'ge-0/0/1': {'is_up': True, 'is_enabled': True, 'description': 'An Interface in bma', 'last_flapped': 83272.0, 'mac_address': '08:00:27:FB:F0:FC', 'speed': 1000}, 'ge-0/0/2': {'is_up': False, 'is_enabled': False, 'description': 'Another interface in bma', 'last_flapped': 82560.0, 'mac_address': '08:00:27:32:60:54', 'speed': 1000}, '.local.': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'dsc': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'gre': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'ipip': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'irb': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': '4C:96:14:8C:76:B0', 'speed': -1}, 'lo0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'lsi': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'mtun': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pimd': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pime': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pp0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'ppd0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'ppe0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'st0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'tap': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'vlan': {'is_up': False, 'is_enabled': True, 'description': '', 'last_flapped': 83282.0, 'mac_address': '00:00:00:00:00:00', 'speed': 1000}}

Or even reuse::

    >>> def get_facts(task, facts):
    ...     # variable "facts" will let us reuse this for multiple purposes
    ...     r = tasks.napalm_get_facts(task, facts)
    ...     print(task.host.name)
    ...     print("============")
    ...     print(r["result"])
    ...     print()
    ...
    >>> cmh_leaf.run(task=get_facts, facts="facts")
    switch00.cmh
    ============
    {'hostname': 'switch00.bma', 'fqdn': 'switch00.bma.bma.acme.com', 'vendor': 'Arista', 'model': 'vEOS', 'serial_number': '', 'os_version': '4.17.5M-4414219.4175M', 'uptime': 83534, 'interface_list': ['Ethernet1', 'Ethernet2', 'Management1']}

    switch01.cmh
    ============
    {'vendor': 'Juniper', 'model': 'FIREFLY-PERIMETER', 'serial_number': 'a7defdc362ff', 'os_version': '12.1X47-D20.7', 'hostname': 'switch01.bma', 'fqdn': 'switch01.bma.bma.acme.com', 'uptime': 83431, 'interface_list': ['ge-0/0/0', 'gr-0/0/0', 'ip-0/0/0', 'lsq-0/0/0', 'lt-0/0/0', 'mt-0/0/0', 'sp-0/0/0', 'ge-0/0/1', 'ge-0/0/2', '.local.', 'dsc', 'gre', 'ipip', 'irb', 'lo0', 'lsi', 'mtun', 'pimd', 'pime', 'pp0', 'ppd0', 'ppe0', 'st0', 'tap', 'vlan']}

    >>> cmh_leaf.run(task=get_facts, facts="interfaces")
    switch00.cmh
    ============
    {'Ethernet2': {'is_up': False, 'is_enabled': False, 'description': 'Another interface in bma', 'last_flapped': 1511034159.0400095, 'speed': 0, 'mac_address': '08:00:27:AB:42:B6'}, 'Management1': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 1511033376.7963786, 'speed': 1000, 'mac_address': '08:00:27:47:87:83'}, 'Ethernet1': {'is_up': True, 'is_enabled': True, 'description': 'An Interface in bma', 'last_flapped': 1511033362.0302918, 'speed': 0, 'mac_address': '08:00:27:2D:F4:5A'}}

    switch01.cmh
    ============
    {'ge-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 83387.0, 'mac_address': '08:00:27:AA:8C:76', 'speed': 1000}, 'gr-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'ip-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'lsq-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 83388.0, 'mac_address': 'None', 'speed': -1}, 'lt-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': '02:96:14:8C:76:B3', 'speed': 800}, 'mt-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'sp-0/0/0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': 83388.0, 'mac_address': 'Unspecified', 'speed': 800}, 'ge-0/0/1': {'is_up': True, 'is_enabled': True, 'description': 'An Interface in bma', 'last_flapped': 83387.0, 'mac_address': '08:00:27:FB:F0:FC', 'speed': 1000}, 'ge-0/0/2': {'is_up': False, 'is_enabled': False, 'description': 'Another interface in bma', 'last_flapped': 82675.0, 'mac_address': '08:00:27:32:60:54', 'speed': 1000}, '.local.': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'dsc': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'gre': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'ipip': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'irb': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': '4C:96:14:8C:76:B0', 'speed': -1}, 'lo0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'lsi': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'mtun': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pimd': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pime': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'pp0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'ppd0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'ppe0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': 800}, 'st0': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'None', 'speed': -1}, 'tap': {'is_up': True, 'is_enabled': True, 'description': '', 'last_flapped': -1.0, 'mac_address': 'Unspecified', 'speed': -1}, 'vlan': {'is_up': False, 'is_enabled': True, 'description': '', 'last_flapped': 83397.0, 'mac_address': '00:00:00:00:00:00', 'speed': 1000}}
